import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from xhs_content_engine.models import ContentItem
from xhs_content_engine.story_mining import (
    enrich_story_items,
    fallback_story_score,
    fast_story_filter,
    mine_story_candidate,
    story_queries,
    story_semantic_filter,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 14, tzinfo=UTC)


def config():
    return yaml.safe_load((ROOT / "config/story_mining.yaml").read_text())


def make(row, index=0):
    return ContentItem(
        id=row.get("id", f"item-{index}"),
        source="fixture",
        source_type="personal_blog",
        canonical_url=f"https://example.org/{row.get('id', index)}",
        title=row["title"],
        raw_excerpt=row["raw_excerpt"],
        published_at=NOW,
        verification_state="needs_review",
    )


def test_fixture_has_thirty_story_examples():
    rows = json.loads((ROOT / "tests/fixtures/story_examples.json").read_text())
    assert len(rows) >= 30
    assert {row["expected"] for row in rows} == {"strong", "weak", "borderline"}


def test_strong_story_scores_above_weak_news():
    rows = json.loads((ROOT / "tests/fixtures/story_examples.json").read_text())
    strong = [
        fallback_story_score(make(row), config(), NOW)[0]
        for row in rows
        if row["expected"] == "strong"
    ]
    weak = [
        fallback_story_score(make(row), config(), NOW)[0]
        for row in rows
        if row["expected"] == "weak"
    ]
    assert min(strong) > max(weak)


def test_story_candidate_keeps_verbatim_evidence_and_structure():
    row = {
        "title": "I tried AI, but my salary fell",
        "raw_excerpt": "I switched tools at work and later lost income.",
    }
    candidate = mine_story_candidate(make(row), config(), NOW)
    assert candidate.primary_person
    assert candidate.action in candidate.evidence_spans
    assert candidate.result in candidate.evidence_spans
    assert candidate.story_type in {"single_case", "before_after"}


def test_fast_filter_orders_by_fallback_story_score():
    rows = json.loads((ROOT / "tests/fixtures/story_examples.json").read_text())[:3]
    enriched, _ = enrich_story_items([make(row) for row in rows], config(), now=NOW)
    selected = fast_story_filter(enriched, config())
    assert selected
    assert selected == sorted(selected, key=lambda item: -item.fallback_story_score)


def test_semantic_pass_is_bounded_and_queries_are_configured():
    rows = json.loads((ROOT / "tests/fixtures/story_examples.json").read_text())
    enriched, _ = enrich_story_items([make(row) for row in rows], config(), now=NOW)
    selected = story_semantic_filter(enriched, config())
    assert 10 <= len(selected) <= 20
    assert story_queries(config())[0] == "AI + my job"


def test_discussion_viewpoints_are_counted_without_treating_count_as_opinion():
    source = make(
        {"title": "I changed my workflow", "raw_excerpt": "I used AI and my work changed."}
    )
    source.metadata["discussion_viewpoints"] = [
        {"stance": "support", "evidence": "I saved time", "is_first_person": True},
        {"stance": "concern", "evidence": "I lost context", "is_first_person": True},
    ]
    score, flags = fallback_story_score(source, config(), NOW)
    assert flags["first_person_comments"] == 1
    assert flags["multiple_viewpoints"] == 1
    assert score > 0
