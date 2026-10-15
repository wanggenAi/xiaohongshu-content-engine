"""Regression contracts for attention-first selection; all fixtures are synthetic."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from xhs_content_engine.consumer_appeal import (
    ConsumerJudge,
    ThreeSecondJudge,
    ordinary_score,
    strip_tech,
    top_five_ready,
    update_priority,
)
from xhs_content_engine.editorial_calibration import editorial_rank
from xhs_content_engine.models import ContentItem
from xhs_content_engine.publish_selection import absolute_gate

CONFIG = yaml.safe_load((Path(__file__).parents[1] / "config/mass_appeal.yaml").read_text())
NOW = datetime(2026, 10, 16, tzinfo=UTC)


def row():
    return {
        "ordinary_person_appeal": 80,
        "card_stop_score": 80,
        "three_second_test": "STOP",
        "non_tech_strip_test": "PASS",
        "click_reason_pass": True,
        "consumer_human_trigger": 85,
        "personal_relevance_score": 80,
        "story_conflict_score": 75,
        "visual_asset_strength": 80,
        "china_information_gap_score": 25,
        "source_heat": 80,
        "viral_potential": 70,
        "social_heat": 80,
        "mass_appeal_score": 80,
        "stop_scroll_score": 80,
        "title_potential_score": 80,
        "non_tech_reader_score": 80,
        "programmer_bias_score": 20,
        "calibration_complete": True,
        "headline_claim_status": "PASS",
        "headline_strength": 80,
        "hard_gates": {
            k: "PASS" for k in ("evidence", "scope", "safety", "fabrication", "card_claim")
        },
    }


def test_high_evidence_and_programmer_heat_cannot_buy_consumer_priority():
    strong = row()
    weak = row()
    weak.update(
        ordinary_person_appeal=25,
        card_stop_score=25,
        consumer_human_trigger=20,
        personal_relevance_score=20,
        story_conflict_score=15,
        source_heat=100,
        evidence_fitness=100,
        viral_pattern_similarity=100,
    )
    update_priority(strong, CONFIG)
    update_priority(weak, CONFIG)
    assert strong["final_editorial_priority"] > weak["final_editorial_priority"] + 35
    before = strong["final_editorial_priority"]
    strong.update(evidence_fitness=0, viral_pattern_similarity=0, mass_appeal_score=0)
    update_priority(strong, CONFIG)
    assert strong["final_editorial_priority"] == before
    strong["source_heat"] = 0
    update_priority(strong, CONFIG)
    assert before - strong["final_editorial_priority"] == pytest.approx(2.4)


@pytest.mark.parametrize(
    "field,value",
    [
        ("three_second_test", "SCROLL"),
        ("non_tech_strip_test", "FAIL"),
        ("ordinary_person_appeal", 25),
        ("click_reason_pass", False),
    ],
)
def test_consumer_gate_cannot_be_overridden_by_rank_or_perfect_legacy_scores(field, value):
    data = row()
    data.update(final_editorial_priority=100, mass_appeal_score=100, social_heat=100)
    data[field] = value
    assert absolute_gate(data, CONFIG["gate"], 40, NOW, NOW)[0] != "AUTO_PUBLISH_ELIGIBLE"
    assert not top_five_ready(data)


def test_blind_three_second_request_cannot_see_evidence_or_scoring():
    item = ContentItem(
        id="synthetic",
        source="hacker_news",
        source_type="manual",
        canonical_url="https://example.org",
        title="Technical importance",
        raw_excerpt="PR and source details must not enter card test",
        metadata={
            "attention_card": {"title": "合成标题", "cover_line": "合成封面"},
            "source_heat": 100,
            "ordinary_person_appeal": 100,
        },
    )
    request, _ = ThreeSecondJudge({"provider": {"model": "test"}}, {}, None).prepare(item)
    assert request["state"] == {"title": "合成标题", "cover_line": "合成封面"}
    assert set(request["questions"]["reaction"]["criteria"]) == {"STOP", "MAYBE", "SCROLL"}


def test_consumer_judgment_has_no_heat_input_and_requests_all_human_dimensions():
    item = ContentItem(
        id="synthetic",
        source="hacker_news",
        source_type="manual",
        canonical_url="https://example.org",
        title="test",
        engagement_metrics={"points": 10000},
        metadata={"consumer_evaluation": {"facts": "合成事实", "click_options": {}}},
    )
    request, _ = ConsumerJudge({"provider": {"model": "test"}}, {}, None).prepare(item)
    assert request["state"] == {"facts": "合成事实"}
    assert {
        "money",
        "work",
        "relationship",
        "privacy",
        "surprise",
        "personal_relevance",
        "human_story_conflict",
        "concrete_incident",
        "strip_interest",
    } <= set(request["questions"])


def test_one_strong_relationship_trigger_does_not_need_money_or_tech_importance():
    dims = {k: 0 for k in ("money", "work", "relationship", "privacy", "surprise")}
    dims.update(
        relationship=95,
        personal_relevance=80,
        human_story_conflict=90,
        concrete_incident=90,
        strip_interest=80,
    )
    assert ordinary_score(dims) > 85
    assert "API" not in strip_tech("某模型发布新API和GPU推理框架")
    assert "自己点按钮" in strip_tech("AI让电脑自己点按钮")


def test_scroll_and_unverified_cards_stay_below_supported_attention_cards():
    good = row()
    update_priority(good, CONFIG)
    scroll = deepcopy(good)
    scroll.update(three_second_test="SCROLL", final_editorial_priority=100)
    unsupported = deepcopy(good)
    unsupported["hard_gates"]["card_claim"] = "FAIL"
    assert editorial_rank(good) > editorial_rank(scroll)
    assert editorial_rank(good) > editorial_rank(unsupported)


def test_diversity_only_resolves_close_qualified_cards():
    from xhs_content_engine.editorial_calibration import rank_rows

    cards = []
    for i, (trigger, score) in enumerate(
        [
            ("surprise", 90),
            ("surprise", 89),
            ("surprise", 88),
            ("surprise", 87),
            ("surprise", 86),
            ("relationship", 85),
            ("money", 50),
        ]
    ):
        data = row()
        data.update(id=str(i), core_human_trigger=trigger, final_editorial_priority=score)
        cards.append(data)
    ordered = rank_rows(cards)
    assert ordered[0]["id"] == "0"
    assert any(r["core_human_trigger"] == "relationship" for r in ordered[:5])
    assert not any(r["core_human_trigger"] == "money" for r in ordered[:5])


def test_missing_click_reason_cannot_fall_back_to_generic_curiosity():
    from xhs_content_engine.consumer_appeal import click_options

    assert click_options({}) == []


def test_editor_written_click_reasons_cannot_change_consumer_scores_or_fact_gates():
    item = ContentItem(
        id="synthetic",
        source="test",
        source_type="manual",
        canonical_url="https://example.org",
        title="test",
        metadata={
            "consumer_evaluation": {
                "facts": "固定合成事实",
                "click_options": {"0": "编辑写得极煽动的一段点击理由"},
            }
        },
    )
    judge = ConsumerJudge({"provider": {"model": "test"}}, {}, None)
    before = judge.prepare(item)
    item.metadata["consumer_evaluation"]["click_options"] = {"0": "完全不同的解释"}
    assert judge.prepare(item) == before
    assert "click_reason" not in before[0]["questions"]


def test_pure_wow_can_qualify_without_personal_stakes_or_a_first_person_story():
    dims = {
        k: 0
        for k in (
            "money",
            "work",
            "relationship",
            "privacy",
            "personal_relevance",
            "human_story_conflict",
        )
    }
    dims.update(surprise=95, concrete_incident=90, strip_interest=90)
    assert ordinary_score(dims) >= 90
    dims.update(surprise=10, strip_interest=20)
    assert ordinary_score(dims) < 40  # A concrete, dull company announcement is still dull.
