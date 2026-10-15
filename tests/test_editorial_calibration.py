from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from xhs_content_engine.editorial_calibration import (
    HomepageBlindJudge,
    evidence_profile,
    generate_headlines,
    visual_strength,
)
from xhs_content_engine.models import ContentItem
from xhs_content_engine.publish_selection import absolute_gate
from xhs_content_engine.storage import Store
from xhs_content_engine.viral_references import structural_similarity

CONFIG = yaml.safe_load((Path(__file__).parents[1] / "config/mass_appeal.yaml").read_text())
NOW = datetime(2026, 10, 15, tzinfo=UTC)


def strong():
    return {
        "mass_appeal_score": 80,
        "viral_potential": 72,
        "social_heat": 85,
        "final_editorial_priority": 80,
        "stop_scroll_score": 80,
        "title_potential_score": 80,
        "non_tech_reader_score": 80,
        "programmer_bias_score": 20,
        "calibration_complete": True,
        "headline_claim_status": "PASS",
        "headline_strength": 80,
        "score_confidence_pass": True,
        "hard_gates": {k: "PASS" for k in ("evidence", "scope", "safety", "fabrication")},
        # These are deliberately conflicting obsolete booleans.
        "stop_scroll_test": "FAIL",
        "title_potential_test": "FAIL",
        "evidence_test": "FAIL",
    }


def test_old_random_soft_booleans_cannot_kill_strong_calibrated_topic():
    assert absolute_gate(strong(), CONFIG["gate"], 20, NOW, NOW)[0] == "AUTO_PUBLISH_ELIGIBLE"


@pytest.mark.parametrize("hard", ["evidence", "scope", "safety", "fabrication"])
def test_hard_failure_cannot_be_bought_with_perfect_interest(hard):
    row = strong()
    row["hard_gates"][hard] = "FAIL"
    row["final_editorial_priority"] = 100
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "NO_PUBLISH"


def test_borderline_and_evaluator_disagreement_require_review():
    row = strong()
    row["final_editorial_priority"] = 74.99
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "EDITOR_REVIEW_REQUIRED"
    row = strong()
    row["soft_evaluator_disagreements"] = ["stakes"]
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "REVIEW_ONLY"


def test_attributed_reporting_and_official_announcement_do_not_require_e4():
    item = ContentItem(
        id="fixture",
        source="synthetic",
        source_type="manual",
        canonical_url="https://example.org",
        title="Synthetic release",
        raw_excerpt="公司宣布一项功能，尚未开放。",
        metadata={"evidence_status": "primary_source_checked"},
    )
    assert evidence_profile(item) == ("E3", "公司宣布一项功能，尚未开放。")
    item.metadata["evidence_status"] = "readable_reporting_attributed"
    assert evidence_profile(item)[0] == "E2"
    item.metadata["corroboration_urls"] = ["https://example.org/duplicate"]
    assert evidence_profile(item)[0] == "E2"
    item.raw_excerpt = ""
    item.metadata["evidence_status"] = "primary_source_checked"
    assert evidence_profile(item)[0] == "E0"


def test_reference_similarity_is_structural_multi_example_and_not_name_bonus():
    def ref(i, patterns):
        return {"id": str(i), "content_pattern": patterns}

    assert structural_similarity(["big_person_action"], [ref(1, ["big_person_action"])])[0] == 0
    patterns = ["money", "work_identity"]
    assert structural_similarity(patterns, [ref(1, patterns)])[0] <= 60
    assert structural_similarity(patterns, [ref(i, patterns) for i in range(3)])[0] == 100
    assert (
        structural_similarity(["relationship_loss"], [ref(i, patterns) for i in range(3)])[0] == 0
    )


def test_visual_requires_checked_asset_and_distinguishes_simulation_from_real_action():
    item = ContentItem(
        id="v",
        source="fixture",
        source_type="manual",
        canonical_url="https://example.org",
        title="v",
    )
    item.metadata["visual_assets"] = [
        {"url": "https://example.org/video", "kind": "original_video"}
    ]
    assert visual_strength(item) == 0
    item.metadata["visual_assets"][0]["verified_at"] = NOW.isoformat()
    assert visual_strength(item) == 80
    item.metadata["visual_assets"][0]["verified_action"] = True
    assert visual_strength(item) == 100


def test_homepage_blind_judge_sees_only_titles_covers_and_audience(tmp_path):
    cards = [{"title": f"事实标题{i}", "cover_line": f"封面{i}"} for i in range(5)]
    item = ContentItem(
        id="blind",
        source="secret_source",
        source_type="manual",
        canonical_url="https://example.org/private",
        title="secret",
        metadata={"blind_cards": cards, "score": 99, "algorithm_rank": 1},
    )
    judge = HomepageBlindJudge({"provider": {"model": "jev-latest"}}, {}, Store(tmp_path / "db"))
    request, _ = judge.prepare(item)
    assert set(request["state"]) == {"cards", "audience"}
    assert len(request["questions"]) == 10
    assert "secret_source" not in str(request) and "algorithm_rank" not in str(request)


def test_no_source_or_facts_no_invented_twenty_titles():
    item = ContentItem(
        id="empty",
        source="fixture",
        source_type="manual",
        canonical_url="https://example.org",
        title="Unknown API",
    )
    assert generate_headlines(item) == []


def test_good_topic_with_weak_or_unchecked_headline_is_reworked_not_called_bad():
    row = strong()
    row.update(title_potential_score=90, headline_strength=50)
    verdict, reasons = absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)
    assert verdict == "REVIEW_ONLY"
    assert "chosen_headline_needs_improvement" in reasons
    assert row["title_potential_score"] == 90
    row.update(headline_strength=85, headline_claim_status="UNKNOWN")
    assert absolute_gate(row, CONFIG["gate"], 20, NOW, NOW)[0] == "REVIEW_ONLY"


def test_explicit_dislike_cannot_enter_positive_reference_library(tmp_path):
    from xhs_content_engine.publish_selection import feedback_sync
    from xhs_content_engine.viral_references import build_library

    root = Path(__file__).parents[1]
    (tmp_path / "data").mkdir()
    (tmp_path / "data/editorial_feedback.jsonl").write_text(
        (root / "data/editorial_feedback.jsonl").read_text()
    )
    store = Store(tmp_path / "db")
    feedback = feedback_sync(tmp_path, store)
    item = ContentItem(
        id=feedback[0].candidate_id,
        source="fixture",
        source_type="manual",
        canonical_url="https://example.org/negative",
        title="Negative fixture",
        published_at=NOW,
        engagement_metrics={"points": 1000, "comments": 500},
    )
    library = build_library(
        tmp_path, [item], {"model": "fixture", "concurrency": 1}, CONFIG, store, feedback, NOW
    )
    assert library["positive_references"] == []
    assert library["negative_references"][0]["decision"] == "DISLIKE"
