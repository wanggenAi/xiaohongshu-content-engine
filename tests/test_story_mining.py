import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml

from xhs_content_engine.collectors import collect_hn_story_search
from xhs_content_engine.editorial_screening import validate_response
from xhs_content_engine.models import ContentItem
from xhs_content_engine.story_mining import (
    _assign_clusters,
    candidate_from_item,
    compose_story,
    discover_stories,
    enrich_story_items,
    fallback_story_score,
    fast_story_filter,
    mine_story_candidate,
    story_queries,
    story_request,
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


def mock_story_response(source, selections=None, gates=None):
    request = story_request(source, config(), "test")
    selections = selections or {}
    gates = gates or {}
    answers = {}
    for key, question in request["questions"].items():
        if question["type"] == "noul":
            answers[key] = {"type": "noul", "noul": gates.get(key, 0)}
        else:
            chosen = selections.get(key, "NONE")
            answers[key] = {
                "type": "choice",
                "choice": chosen,
                "confidence": 1,
                "probabilities": {k: float(k == chosen) for k in question["criteria"]},
            }
    return validate_response({"model": "test", "answers": answers}, request)


def test_corporate_we_and_intended_benefits_cannot_become_a_personal_story():
    source = make(
        {
            "title": "We will scale AI infrastructure",
            "raw_excerpt": "Our company will deploy chips next year.",
        }
    )
    selections = {field: "s0" for field in config()["structure_fields"]}
    result = compose_story(source, mock_story_response(source, selections), config())
    assert result.story_mining_status == "weak"
    assert result.story_richness_score < 40
    assert not result.story_structure["what_happened"]


def test_unrelated_commenter_result_is_never_joined_to_post_action():
    source = make({"title": "I built an AI tool", "raw_excerpt": "I built a tool for my website."})
    source.metadata["discussion_comments"] = [
        {"evidence": "I lost my job.", "url": "https://example.org/comment", "author": "other"}
    ]
    selection = {"who": "s0", "did_what": "s1", "what_happened": "c0"}
    with pytest.raises(ValueError, match="unknown evidence"):
        mock_story_response(source, selection, {"personal_event": 1, "realized_result": 1})


def test_semantic_story_with_missing_fields_preserves_gaps():
    source = make(
        {
            "title": "I posted a story and got bot traffic",
            "raw_excerpt": "I posted a story. My website was flooded with bot traffic.",
        }
    )
    selection = {"who": "s1", "did_what": "s1", "what_happened": "s2"}
    result = compose_story(
        source,
        mock_story_response(source, selection, {"personal_event": 1, "realized_result": 1}),
        config(),
    )
    assert result.story_mining_status == "candidate"
    assert result.story_structure["before_state"] == ""
    assert result.story_structure["conflict"] == ""
    assert result.claim_scope == "single_case"
    assert candidate_from_item(result).result in source.raw_excerpt


def test_low_authority_personal_cases_survive_discovery_and_similar_titles():
    title = "I tried AI in my team and changed our entire workflow yesterday"
    one = make({"id": "one", "title": title, "raw_excerpt": "I tried it and lost time."})
    two = make({"id": "two", "title": title, "raw_excerpt": "I tried it and gained time."})
    one.source_reliability = two.source_reliability = 0.1
    items = discover_stories([one, two], {"max_age_days": 7}, config(), {}, NOW)
    assert {item.id for item in items} == {"one", "two"}


def test_clusters_require_distinct_known_case_authors_and_never_claim_trend():
    sources = [
        make(
            {
                "id": str(i),
                "title": "I used AI and lost work",
                "raw_excerpt": "I switched tools and lost a client.",
            }
        )
        for i in range(2)
    ]
    for source in sources:
        source.story_structure = {
            "who": "I",
            "did_what": source.title,
            "what_happened": source.raw_excerpt,
        }
        source.metadata.update(
            story_theme="ai_cost", case_author="same", case_url=source.canonical_url
        )
        source.claim_scope = "single_case"
    candidates = [candidate_from_item(s) for s in sources]
    _assign_clusters(sources, candidates)
    assert all(s.claim_scope == "single_case" for s in sources)
    sources[1].metadata["case_author"] = "another"
    _assign_clusters(sources, candidates)
    assert all(s.claim_scope == "multiple_cases" for s in sources)
    assert all(s.claim_scope != "reported_trend" for s in sources)


def test_public_search_uses_config_queries_and_keeps_actual_reply_provenance():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.host == "hn.algolia.com":
            assert request.url.params["query"] == "AI my job"
            return httpx.Response(200, json={"hits": [{"objectID": "1"}]})
        identifier = request.url.path.rsplit("/", 1)[-1]
        records = {
            "1.json": {
                "id": 1,
                "type": "story",
                "title": "My AI job",
                "time": int(NOW.timestamp()),
                "by": "author",
                "kids": [2, 3],
            },
            "2.json": {
                "id": 2,
                "text": "I tried it and saved time.",
                "by": "worker",
                "parent": 1,
                "kids": [4],
            },
            "3.json": {"id": 3, "deleted": True},
            "4.json": {"id": 4, "text": "I lost time instead.", "by": "other", "parent": 2},
        }
        return httpx.Response(200, json=records[identifier])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        items, audit = collect_hn_story_search(
            {"name": "stories", "type": "hn_story_search", "queries": ["AI + my job"]}, http
        )
    comments = items[0]["metadata"]["discussion_comments"]
    assert audit["comment_excerpts"] == 2
    assert comments[1]["parent"] == "2"
    assert all(c["url"].startswith("https://news.ycombinator.com/item?id=") for c in comments)
    assert len(calls) == 5


def test_first_person_alone_does_not_create_strong_story_and_stars_are_not_discussion():
    source = make(
        {"title": "I like this model", "raw_excerpt": "My thoughts about the new release."}
    )
    source.engagement_metrics = {"stars": 300}
    score, flags = fallback_story_score(source, config(), NOW)
    assert flags["action_result_structure"] == 0
    assert flags["discussion_engagement"] == 0
    assert score < 40


def test_queue_orders_story_evidence_above_authoritative_news():
    from xhs_content_engine.human_triggers import human_review_queue

    human_config = yaml.safe_load((ROOT / "config/human_triggers.yaml").read_text())
    news = make(
        {"id": "news", "title": "API release", "raw_excerpt": "Company announces new parameters."}
    )
    story = make(
        {
            "id": "story",
            "title": "I lost my job after AI automation",
            "raw_excerpt": "I switched tools and lost a client.",
        }
    )
    news.score, news.source_reliability = 99, 1
    story.score, story.source_reliability = 1, 0.1
    items, _ = enrich_story_items([news, story], config(), now=NOW)
    queue = human_review_queue(items, [], human_config)
    assert queue[0].id == "story"
    assert all(item.human_trigger_score is None for item in queue)
