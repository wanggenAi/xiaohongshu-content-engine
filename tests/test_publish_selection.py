from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from xhs_content_engine.models import ContentItem
from xhs_content_engine.publish_selection import absolute_gate, candidate_pool, social_heat
from xhs_content_engine.telegram_public import parse_public, public_url

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 14, 14, tzinfo=UTC)
CONFIG = yaml.safe_load((ROOT / "config/mass_appeal.yaml").read_text())


def passing():
    return {
        "ordinary_person_appeal": 80,
        "card_stop_score": 80,
        "three_second_test": "STOP",
        "non_tech_strip_test": "PASS",
        "click_reason_pass": True,
        "mass_appeal_score": 80,
        "viral_potential": 70,
        "social_heat": None,
        "publishability_score": 78,
        "score_confidence_pass": True,
        "stop_scroll_test": "PASS",
        "non_tech_reader_test": "PASS",
        "evidence_test": "PASS",
        "title_potential_test": "PASS",
        "contrarian_check": "PASS",
        "calibration_complete": True,
        "headline_claim_status": "PASS",
        "headline_strength": 80,
        "stop_scroll_score": 80,
        "title_potential_score": 80,
        "final_editorial_priority": 78,
        "non_tech_reader_score": 80,
        "programmer_bias_score": 20,
        "hard_gates": {
            k: "PASS" for k in ("evidence", "scope", "safety", "fabrication", "card_claim")
        },
    }


def test_absolute_thresholds_no_best_of_bad_batch():
    row = passing()
    row.update(viral_potential=39.58, mass_appeal_score=45, final_editorial_priority=42)
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "NO_PUBLISH"
    assert absolute_gate(passing(), CONFIG["gate"], 8, NOW, NOW)[0] == "REVIEW_ONLY"
    row = passing()
    row["final_editorial_priority"] = 74.99
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "EDITOR_REVIEW_REQUIRED"
    assert absolute_gate(passing(), CONFIG["gate"], 20, NOW, NOW)[0] == "AUTO_PUBLISH_ELIGIBLE"


@pytest.mark.parametrize(
    "field",
    [
        "ordinary_person_appeal",
        "three_second_test",
        "non_tech_strip_test",
        "viral_potential",
        "final_editorial_priority",
        "hard_gates",
        "card_stop_score",
        "non_tech_reader_score",
        "programmer_bias_score",
        "calibration_complete",
    ],
)
def test_missing_or_low_confidence_never_publish(field):
    row = passing()
    row.pop(field)
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] != "AUTO_PUBLISH_ELIGIBLE"


def test_expired_scan_and_explicit_dislike_fail():
    assert (
        absolute_gate(passing(), CONFIG["gate"], 20, NOW - timedelta(hours=7), NOW)[0]
        != "AUTO_PUBLISH_ELIGIBLE"
    )
    assert absolute_gate(passing(), CONFIG["gate"], 20, NOW, NOW, disliked=True)[0] == "NO_PUBLISH"


def test_extreme_heat_only_replaces_viral_threshold():
    row = passing()
    row.update(viral_potential=40, social_heat=90)
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "AUTO_PUBLISH_ELIGIBLE"
    row["non_tech_reader_score"] = 40
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "REVIEW_ONLY"


def test_unknown_heat_is_not_fabricated():
    item = ContentItem(
        id="a", source="news", source_type="rss", canonical_url="https://example.org/a", title="a"
    )
    assert social_heat(item, CONFIG) is None
    item.engagement_metrics = {"points": 1000, "comments": 500}
    assert social_heat(item, CONFIG) == 100


def test_multi_lane_pool_does_not_require_story_and_dedupes_event():
    lanes = yaml.safe_load((ROOT / "config/content_lanes.yaml").read_text())
    people = yaml.safe_load((ROOT / "config/watch_people.yaml").read_text())
    items = [
        ContentItem(
            id=str(i),
            source="official",
            source_type="rss",
            canonical_url=f"https://example.org/{i}",
            title=f"Company action number {i}",
            raw_excerpt="Meaningful action",
            published_at=NOW,
            metadata={"event_key": "event", "lane": "GLOBAL_HOT_TOPIC"},
        )
        for i in range(3)
    ]
    selected, pool = candidate_pool(items, people, lanes, NOW)
    assert len(selected) == len(pool) == 1
    assert selected[0].story_richness_score == 0


@pytest.mark.parametrize(
    "url",
    [
        "https://t.me/+secret",
        "https://t.me/joinchat/secret",
        "https://t.me/c/123/456",
        "http://t.me/aipost",
        "https://evil.com/aipost",
        "https://t.me/aipost/not-a-post",
        "https://t.me/share/url",
    ],
)
def test_private_and_service_telegram_urls_rejected(url):
    with pytest.raises(ValueError):
        public_url(url)


def test_public_telegram_post_real_text_time_views():
    html = (
        '<div class="tgme_widget_message" data-post="aipost/123"><div clas'
        's="tgme_widget_message_text">Real <b>public</b> post</div><a clas'
        's="tgme_widget_message_date"><time datetime="2026-10-14T01:00:00+'
        '00:00">01:00</time></a><span class="tgme_widget_message_views">12'
        ".3K</span></div>"
    )
    rows = parse_public(html, "aipost")
    assert public_url("https://t.me/aipost/123") == "https://t.me/s/aipost/123"
    assert len(rows) == 1 and rows[0]["engagement_metrics"] == {"views": 12300}
    assert rows[0]["raw_excerpt"] == "Real public post"
    assert rows[0]["metadata"]["evidence_status"] == "public_post_unverified_claims"
    assert parse_public("Please log in to Telegram", "aipost") == []


def test_blind_click_request_has_no_sources_or_scores(tmp_path):
    from xhs_content_engine.publish_selection import BlindClickJudge
    from xhs_content_engine.storage import Store

    item = ContentItem(
        id="title",
        source="secret_source",
        source_type="manual",
        canonical_url="https://example.org/secret",
        title="secret fact",
        metadata={"headline_options": [(f"事实标题{i}") for i in range(20)]},
    )
    judge = BlindClickJudge(
        {"provider": {"model": "jev-latest"}}, {}, Store(tmp_path / "db.sqlite")
    )
    request, _ = judge.prepare(item)
    assert set(request["state"]) == {"headlines", "audience"}
    assert "secret_source" not in str(request) and "example.org" not in str(request)
    assert len(request["questions"]["winner"]["criteria"]) == 20


def test_feedback_quote_and_reason_preserved_idempotently(tmp_path):
    from xhs_content_engine.publish_selection import feedback_sync
    from xhs_content_engine.storage import Store

    (tmp_path / "data").mkdir()
    ledger = tmp_path / "data/editorial_feedback.jsonl"
    ledger.write_text((ROOT / "data/editorial_feedback.jsonl").read_text())
    store = Store(tmp_path / "db.sqlite")
    first = feedback_sync(tmp_path, store)
    second = feedback_sync(tmp_path, store)
    assert len(first) == len(second) == 1
    assert second[0].decision == "DISLIKE"
    assert second[0].user_quote == "一点都不吸引人。"
    assert "best_of_bad_batch" in second[0].reasons


def test_actual_published_weak_candidate_cannot_pass_new_gate():
    import json

    receipt = json.loads((ROOT / "data/published_posts.jsonl").read_text().splitlines()[-1])
    row = passing()
    row.update(viral_potential=receipt["viral_potential"], social_heat=None)
    verdict, failures = absolute_gate(row, CONFIG["gate"], 40, NOW, NOW, disliked=True)
    assert verdict == "NO_PUBLISH"
    assert "explicit_user_DISLIKE" in failures
    assert "insufficient_viral_heat_or_grounded_reference_match" in failures


def test_major_topic_beats_complete_niche_story_without_story_bonus():
    from xhs_content_engine.editorial_screening import JudgmentResponse
    from xhs_content_engine.publish_selection import compose

    def response(score, viral):
        answers = {
            key: {"type": "score", "score": score, "confidence": 1} for key in CONFIG["levels"]
        }
        answers["viral_potential"]["score"] = viral
        answers["lane"] = {"type": "choice", "choice": "GLOBAL_HOT_TOPIC", "confidence": 1}
        answers.update(
            {
                key: {"type": "noul", "noul": 1}
                for key in [
                    "stop_scroll",
                    "non_tech_reader",
                    "evidence",
                    "title_potential",
                    "hot_news",
                ]
            }
        )
        answers["contrarian"] = {"type": "noul", "noul": 0}
        return JudgmentResponse.model_validate({"model": "SYNTHETIC_TEST_ONLY", "answers": answers})

    packet = {
        "proposed_headline": "知名公司改变普通人的工作",
        "stop_scroll_reason": "一个已经核验的具体工作变化。",
        "interest_reason": "真实工作影响。",
    }
    base = dict(
        source="SYNTHETIC_TEST_ONLY",
        source_type="manual",
        published_at=NOW,
        raw_excerpt="synthetic fixture, never collected",
        metadata={"editorial_packet": packet, "evidence_status": "primary_source_checked"},
    )
    major = ContentItem(
        id="major",
        title="重大工作变化",
        canonical_url="https://example.org/major",
        story_richness_score=0,
        **base,
    )
    niche = ContentItem(
        id="niche",
        title="陌生开发者的完整故事",
        canonical_url="https://example.org/niche",
        story_richness_score=100,
        **base,
    )
    strong = compose(major, response(4, 4), "test", None, CONFIG, 20, NOW, NOW, False)
    weak = compose(niche, response(1, 1), "test", None, CONFIG, 20, NOW, NOW, False)
    assert strong["mass_appeal_score"] > weak["mass_appeal_score"]
    assert strong["publishability_score"] > weak["publishability_score"]
    assert weak["verdict"] == "NO_PUBLISH"


def test_event_dedupe_retains_discussion_heat_with_primary_evidence():
    lanes = yaml.safe_load((ROOT / "config/content_lanes.yaml").read_text())
    people = yaml.safe_load((ROOT / "config/watch_people.yaml").read_text())
    primary = ContentItem(
        id="primary",
        source="official",
        source_type="rss",
        canonical_url="https://example.org/launch",
        title="Official launch",
        published_at=NOW,
        raw_excerpt="Official verified text",
        metadata={"event_key": "launch", "editorial_packet": {"topic": "event"}},
    )
    discussion = ContentItem(
        id="discussion",
        source="hn",
        source_type="hn",
        canonical_url="https://example.org/discussion",
        title="Discussion of same launch",
        published_at=NOW,
        engagement_metrics={"points": 1000, "comments": 500},
        metadata={
            "event_key": "launch",
            "discussion_url": "https://news.ycombinator.com/item?id=123",
        },
    )
    selected, pool = candidate_pool([primary, discussion], people, lanes, NOW, CONFIG)
    assert len(pool) == 1 and selected[0].id == "primary"
    assert selected[0].raw_excerpt == "Official verified text"
    assert social_heat(selected[0], CONFIG) == 100
    assert selected[0].metadata["engagement_evidence"][0]["url"].endswith("123")
    assert (
        selected[0].metadata["heat_scope"]
        == "same_event_public_discussion_not_specific_demo_clicks"
    )
