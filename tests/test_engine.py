import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from xhs_content_engine.__main__ import app
from xhs_content_engine.collectors import SkipSource, telegram_batch
from xhs_content_engine.editorial import export, mask_public, packet, public_brief, validate_public
from xhs_content_engine.models import ContentItem, ContentPerformance
from xhs_content_engine.normalize import canonicalize, normalize
from xhs_content_engine.pipeline import Pipeline
from xhs_content_engine.ranking import dedupe, rank, score

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 14, tzinfo=UTC)


@pytest.fixture
def config():
    return yaml.safe_load((ROOT / "config/scoring.yaml").read_text())


@pytest.fixture
def style():
    return yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())


@pytest.fixture
def pipeline(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    return Pipeline(tmp_path)


def item(**updates):
    data = dict(
        id="one",
        source="hacker_news",
        source_type="hacker_news",
        canonical_url="https://example.org/new-model",
        title="New AI model for teachers",
        published_at=NOW,
        fetched_at=NOW,
        author="Alice",
        raw_excerpt="A source excerpt.",
        public_source_label="海外开发者社区",
        engagement_metrics={"points": 100},
    )
    return ContentItem(**(data | updates))


def test_validation():
    with pytest.raises(ValidationError):
        item(canonical_url="file:///etc/passwd")
    with pytest.raises(ValidationError):
        item(published_at=datetime(2026, 10, 14))
    with pytest.raises(ValidationError):
        item(source_reliability=2)
    with pytest.raises(ValidationError):
        item(engagement_metrics={"likes": -1})


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://Example.com/a?utm_source=x&b=2&a=1#part", "https://example.com/a?a=1&b=2"),
        ("https://telegram.me/s/SomeChannel/42?single", "https://t.me/somechannel/42"),
        ("http://t.me/SomeChannel/42?embed=1", "https://t.me/somechannel/42"),
        ("https://example.org/?id=2", "https://example.org/?id=2"),
    ],
)
def test_canonicalization(url, expected):
    assert canonicalize(url) == expected


def test_duplicate_provenance():
    first = item(metadata={"original_url": "https://news.ycombinator.com/item?id=42"})
    second = item(id="two", source="publisher", source_type="rss", source_reliability=0.9)
    result = dedupe([first, second])
    assert len(result) == 1
    assert {p["source"] for p in result[0].metadata["provenance"]} == {"hacker_news", "publisher"}
    assert result[0].metadata["provenance"][0]["original_url"].endswith("id=42")
    assert len(dedupe([first, item(id="other", canonical_url="https://other.org/new")])) == 2


def test_transitive_duplicate_groups():
    title = "A long precise title about a specific new artificial intelligence research result"
    a = item(id="a", title=title)
    b = item(id="b", title="Another title", canonical_url=a.canonical_url)
    c = item(id="c", title=title, canonical_url="https://other.org/research")
    assert len(dedupe([a, b, c])) == 1


def test_scoring_is_explained(config):
    fresh = score(item(), config, NOW)
    old = score(item(published_at=NOW - timedelta(days=20)), config, NOW)
    assert fresh.score > old.score
    assert "stale" in old.score_breakdown["penalties"]
    breakdown = fresh.score_breakdown
    assert fresh.score == round(
        max(0, sum(breakdown["weighted"].values()) - sum(breakdown["penalties"].values())), 2
    )
    assert "ai" in breakdown["keyword_evidence"]["china_relevance"]
    assert 0 <= fresh.score <= 100


def test_unknown_dates_and_future_do_not_rank(config):
    assert (
        rank(
            [item(published_at=None), item(id="future", published_at=NOW + timedelta(days=1))],
            config,
            now=NOW,
        )
        == []
    )


def test_ranking_diversity(config):
    items = [
        item(id=str(i), title=f"New AI career model {i}", canonical_url=f"https://example.org/{i}")
        for i in range(10)
    ]
    assert len(rank(items, config, now=NOW)) == config["max_per_source"]
    assert rank([], config, now=NOW) == []


def test_editorial_and_public_separation(tmp_path, style, config):
    candidate = score(
        item(
            title="Telegram and Reddit debate X AI on Hacker News",
            source="telegram",
            source_type="telegram_bot",
        ),
        config,
        NOW,
    )
    internal = packet(candidate, style)
    assert "Telegram" in internal and "https://example.org/new-model" in internal
    assert "Key viewpoints" in internal and "Rights / Attribution Notes" in internal
    brief = public_brief(candidate, style)
    validate_public(brief, style)
    assert "Telegram" not in brief and "Reddit" not in brief
    folder = export([candidate], tmp_path, style, NOW)
    assert len(list(folder.glob("*.md"))) == 1
    export([], tmp_path, style, NOW)
    assert not list(folder.glob("*.md"))


@pytest.mark.parametrize(
    "word",
    [
        "Telegram",
        "telegram",
        "TELEGRAM",
        "Reddit",
        "X",
        "Twitter",
        "Hacker News",
        "hacker_news",
        "Discord",
        "GitHub",
        "t.me",
    ],
)
def test_public_draft_policy(word, style):
    draft = f"最近{word}上有人发布新内容。"
    with pytest.raises(ValueError):
        validate_public(draft, style)
    validate_public(mask_public(draft, style), style)


def test_manual_inbox_cli(pipeline):
    result = CliRunner().invoke(
        app,
        [
            "inbox",
            "add",
            "https://telegram.me/TestChannel/12?single",
            "--root",
            str(pipeline.root),
            "--title",
            "A real human story",
            "--note",
            "User supplied excerpt",
        ],
    )
    assert result.exit_code == 0, result.output
    pipeline.sources = {"sources": []}
    audit = pipeline.collect()
    candidate = pipeline.store.items()[0]
    assert audit["raw_items_this_run"] == 1
    assert candidate.source == "telegram"
    assert candidate.canonical_url == "https://t.me/testchannel/12"
    assert candidate.published_at is None
    assert candidate.metadata["original_platform"] == "telegram"
    pipeline.store.add_inbox(candidate.canonical_url)
    assert pipeline.store.inbox()[0]["title"] == "A real human story"


def test_source_failure_isolation(pipeline):
    pipeline.sources = {
        "sources": [
            {"name": "broken", "type": "rss", "url": "https://broken.org/feed"},
            {"name": "works", "type": "rss", "url": "https://works.org/feed"},
            {"name": "empty", "type": "rss", "url": "https://empty.org/feed"},
        ]
    }

    def handler(request):
        if request.url.host == "broken.org":
            return httpx.Response(500)
        entry = (
            ""
            if request.url.host == "empty.org"
            else (
                "<item><title>New AI robot</title><link>https://works.org/story</link>"
                "<pubDate>Wed, 14 Oct 2026 00:00:00 GMT</pubDate></item>"
            )
        )
        return httpx.Response(200, text=f"<rss version='2.0'><channel>{entry}</channel></rss>")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        report = pipeline.collect(http)
    statuses = {r["source"]: r["status"] for r in report["sources"]}
    assert statuses == {"broken": "error", "works": "ok", "empty": "empty", "manual_inbox": "empty"}
    assert len(pipeline.store.items()) == 1


def update(identifier=42, **overrides):
    post = {
        "message_id": 12,
        "date": int(NOW.timestamp()),
        "chat": {"type": "channel", "username": "TestChannel", "title": "Test"},
        "text": "New AI model\nA bounded real excerpt",
        **overrides,
    }
    return {"update_id": identifier, "channel_post": post}


def test_telegram_missing_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(SkipSource, match="missing"):
        telegram_batch({}, None, 0)


def test_telegram_unauthorized_empty_protected_and_edits(monkeypatch, style):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-secret")
    config = {"name": "telegram", "type": "telegram_bot", "channels": ["@testchannel"]}
    updates = [
        update(),
        update(43, chat={"type": "channel", "username": "Unlisted"}),
        update(44, has_protected_content=True),
        update(45, text=""),
        {"update_id": 46, "edited_channel_post": update()["channel_post"]},
    ]
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"ok": True, "result": updates})
        )
    ) as http:
        raw, offset, size, rejected = telegram_batch(config, http, 0)
    assert (offset, size, rejected) == (47, 5, 3)
    items = [normalize(row, style["public_labels"]) for row in raw]
    assert items[0].id == items[1].id
    assert items[0].engagement_metrics == {}
    assert items[0].author == "Test"
    assert items[0].public_source_label == "海外社区"


def test_telegram_offset_saved_before_next_batch_and_resume(pipeline, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-secret")
    pipeline.sources = {
        "sources": [
            {
                "name": "telegram",
                "type": "telegram_bot",
                "channels": ["TestChannel"],
                "max_batches": 2,
            }
        ]
    }
    seen = []

    def handler(request):
        offset = int(request.url.params["offset"])
        seen.append(offset)
        if offset == 0:
            posts = [update(i, message_id=i) for i in range(1, 101)]
            return httpx.Response(200, json={"ok": True, "result": posts})
        assert pipeline.store.get_state("telegram_offset") == 101
        assert len(pipeline.store.items()) == 100
        return httpx.Response(200, json={"ok": True, "result": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        pipeline.collect(http)
        pipeline.collect(http)
    assert seen == [0, 101, 101]
    assert len(pipeline.store.items()) == 100


def test_telegram_failure_does_not_leak_token(pipeline, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-not-in-report")
    pipeline.sources = {
        "sources": [{"name": "telegram", "type": "telegram_bot", "channels": ["TestChannel"]}]
    }
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(409))) as http:
        report = pipeline.collect(http)
    assert "secret-not-in-report" not in json.dumps(report)
    assert report["sources"][0]["http_status"] == 409
    assert pipeline.store.get_state("telegram_offset") is None


def test_invalid_telegram_does_not_acknowledge(pipeline, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-secret")
    pipeline.sources = {
        "sources": [{"name": "telegram", "type": "telegram_bot", "channels": ["TestChannel"]}]
    }
    post = update(chat={"type": "channel", "username": "TestChannel", "title": "Test"})
    # Malformed username matched by config still produces an invalid URL.
    post["channel_post"]["chat"]["username"] = "bad:invalid"
    pipeline.sources["sources"][0]["channels"] = ["bad:invalid"]
    # A normalizer error must not advance the cursor.
    monkeypatch.setattr(pipeline, "save_raw", lambda raw: ([], 1))
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"ok": True, "result": [post]})
        )
    ) as http:
        report = pipeline.collect(http)
    assert report["sources"][0]["status"] == "error"
    assert pipeline.store.get_state("telegram_offset") is None


def test_performance_persistence(pipeline):
    record = ContentPerformance(
        id="post-1",
        published_at=NOW,
        topic="AI learning",
        content_type="AI_PRODUCT",
        title="Test",
        internal_source="telegram",
        public_source_label="海外社区",
        metrics_24h={"views": 10, "saves": 2},
    )
    pipeline.store.save_performance(record)
    stored = pipeline.store.db.execute("SELECT body FROM content_performance").fetchone()[0]
    assert json.loads(stored)["internal_source"] == "telegram"
    with pytest.raises(ValidationError):
        record.model_copy().model_validate(record.model_dump() | {"metrics_2h": {"views": -1}})
