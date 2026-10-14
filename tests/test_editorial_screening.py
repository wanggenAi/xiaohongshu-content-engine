import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml
from typer.testing import CliRunner

from xhs_content_engine.__main__ import app
from xhs_content_engine.editorial import export, public_brief, validate_public
from xhs_content_engine.editorial_screening import (
    SemanticJudge,
    compose_assessment,
    evidence_spans,
    judgment_request,
    select_screened,
    validate_response,
)
from xhs_content_engine.models import ContentItem, EditorialFeedback
from xhs_content_engine.pipeline import Pipeline
from xhs_content_engine.storage import Store

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 14, tzinfo=UTC)


@pytest.fixture
def config():
    return yaml.safe_load((ROOT / "config/editorial_scoring.yaml").read_text())


@pytest.fixture
def lenses():
    return yaml.safe_load((ROOT / "config/editorial_lenses.yaml").read_text())["lenses"]


@pytest.fixture
def style():
    return yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "content.sqlite3")


def candidate(**overrides):
    return ContentItem(
        **(
            dict(
                id="unseen-case",
                source="reporter",
                source_type="rss",
                canonical_url="https://example.org/worker-story",
                score=40,
                title="A studio requires designers to use generated artwork instead of drawing",
                raw_excerpt=(
                    "Ten designers said the new rule changed their review work and accountability."
                ),
                author="A reporter",
                published_at=NOW,
            )
            | overrides
        )
    )


def response_for(request, *, level=3, lens="creative_work", reject=None, signals=True):
    """An independent typed provider fixture; live quality is separately backtested."""
    answers = {}
    for key, question in request["questions"].items():
        if question["type"] == "score":
            n = min(level, len(question["criteria"]) - 1)
            answers[key] = {
                "type": "score",
                "score": n,
                "confidence": 1,
                "probabilities": {str(i): float(i == n) for i in range(len(question["criteria"]))},
            }
        elif question["type"] == "noul":
            answers[key] = {"type": "noul", "noul": float(key == f"reject_{reject}")}
        else:
            choice = lens if key == "lens" else ("s0" if signals else "NONE")
            answers[key] = {
                "type": "choice",
                "choice": choice,
                "confidence": 1,
                "probabilities": {
                    option: float(option == choice) for option in question["criteria"]
                },
            }
    return {
        "model": "jev-test",
        "answers": answers,
        "usage": {"input_tokens": 100, "output_tokens": 30},
    }


def assessment(item, config, lenses, **kwargs):
    request = judgment_request(item, config, lenses)
    response = validate_response(response_for(request, **kwargs), request)
    return compose_assessment(item, response, config, lenses)


def test_editorial_score_separate_and_explained(config, lenses):
    result = assessment(candidate(), config, lenses)
    assert result.discovery_score == result.score == 40
    assert result.editorial_score == round(
        sum(result.editorial_score_breakdown["weighted"].values())
        + result.editorial_score_breakdown["decision_risk_adjustment"],
        2,
    )
    assert result.editorial_score > 70
    assert result.editorial_verdict == "STRONG"
    assert result.editorial_score_breakdown["dimensions"]["novelty"] <= 0.35
    assert "中文报道饱和度尚未调查" in result.missing_evidence


@pytest.mark.parametrize(
    "reason",
    [
        "TOO_TECHNICAL",
        "PR_ONLY",
        "MINOR_UPDATE",
        "NO_HUMAN_ANGLE",
        "NO_STORY",
        "LOW_CHINA_RELEVANCE",
        "WEAK_EVIDENCE",
        "BORING",
    ],
)
def test_hard_reject_overrides_high_discovery_and_editorial_scores(reason, config, lenses):
    result = assessment(candidate(score=99), config, lenses, reject=reason)
    assert result.editorial_score > 70
    assert result.editorial_verdict == "REJECT"
    assert reason in result.editorial_reject_reason
    assert select_screened([result], config, 5)[1] == []


def test_saturation_requires_actual_chinese_coverage_evidence(config, lenses):
    unaudited = assessment(candidate(), config, lenses, reject="SATURATED")
    audited = assessment(
        candidate(
            metadata={
                "chinese_coverage": {
                    "status": "saturated",
                    "evidence_urls": ["https://example.cn/report"],
                }
            }
        ),
        config,
        lenses,
        reject="SATURATED",
    )
    assert "SATURATED" not in unaudited.editorial_reject_reason
    assert "SATURATED" in audited.editorial_reject_reason


def test_boring_and_technical_content_cannot_gain_from_ai_keywords(config, lenses):
    ordinary = candidate(
        title="New first AI infrastructure release v9.1",
        raw_excerpt="Vendor announces a parameter and a normal financing round.",
    )
    boring = assessment(ordinary, config, lenses, level=0, lens="NONE", signals=False)
    human = assessment(candidate(), config, lenses)
    assert boring.editorial_score < human.editorial_score
    assert "BORING" in boring.editorial_reject_reason
    assert "NO_HUMAN_ANGLE" in boring.editorial_reject_reason
    assert "LOW_CHINA_RELEVANCE" in boring.editorial_reject_reason
    assert select_screened([boring, human], config, 5)[1] == [human]


def test_specific_headline_only_remains_possible_not_verified(config, lenses):
    story = assessment(candidate(raw_excerpt=""), config, lenses)
    assert story.editorial_score_breakdown["dimensions"]["evidence_quality"] <= 0.25
    assert story.verification_state == "needs_review"
    assert any("只有标题" in text for text in story.missing_evidence)


def test_story_signals_are_copied_from_evidence_not_generated(config, lenses):
    source = candidate(raw_excerpt="The team changed from 12 people to 3 people in review roles.")
    result = assessment(source, config, lenses)
    spans = set(evidence_spans(source).values())
    assert all(
        quote in spans
        for key, values in result.story_signals.items()
        if key != "numbers"
        for quote in values
    )
    assert "12 people" in result.story_signals["numbers"]
    assert "3 people" in result.story_signals["numbers"]
    assert any("12 people" in q for q in result.editorial_questions)


def test_multiple_valid_spans_do_not_drop_a_supported_signal(config, lenses):
    source = candidate()
    request = judgment_request(source, config, lenses)
    data = response_for(request)
    data["answers"]["signal_person"].update(
        choice="s0", confidence=0.2, probabilities={"s0": 0.75, "s1": 0.15, "NONE": 0.1}
    )
    result = compose_assessment(source, validate_response(data, request), config, lenses)
    assert result.story_signals["person"] == [source.title]


def test_questions_and_angles_follow_the_specific_consequence(config, lenses):
    work = assessment(candidate(), config, lenses)
    control = assessment(
        candidate(id="control", title="People can change their feed settings"),
        config,
        lenses,
        lens="user_control",
    )
    assert work.editorial_questions != control.editorial_questions
    assert work.possible_angles != control.possible_angles
    assert "工作要求" in "".join(work.possible_angles)
    assert "推荐" in "".join(control.editorial_questions)
    assert len(work.editorial_value["deep_answers"]) == 10


@pytest.mark.parametrize(
    "original",
    [
        "Show HN: A project",
        "Ask HN: A question",
        "Telegram announced a story",
        "GitHub repo launch",
    ],
)
def test_natural_chinese_seed_is_not_platform_replacement(original, config, lenses, style):
    result = assessment(candidate(title=original), config, lenses)
    assert "手写代码" in result.editorial_title_seed
    assert original not in public_brief(result, style)
    validate_public(public_brief(result, style), style)


@pytest.mark.parametrize("text", ["Show 海外: test", "Ask 海外：问题", "海外 post", "Launch 海外"])
def test_mechanical_strings_are_rejected(text, style):
    with pytest.raises(ValueError):
        validate_public(text, style)


def test_fewer_than_limit_and_no_quota_filler(config, lenses, style, tmp_path):
    good = assessment(candidate(), config, lenses)
    weak = assessment(
        candidate(id="pr", source="different-vendor"),
        config,
        lenses,
        level=0,
        signals=False,
        lens="NONE",
    )
    stage_b, deep = select_screened([good, weak], config, source_cap=5, limit=10)
    assert stage_b == deep == [good]
    export(deep, tmp_path, style, NOW)
    review = (tmp_path / "editorial_review.md").read_text()
    assert "Deep Candidates：1" in review and "REJECT" not in review
    validate_public(review, style)


def test_feedback_cli_persistence_and_validation(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    file = tmp_path / "feedback.json"
    file.write_text(
        json.dumps(
            {
                "candidate_id": "unseen",
                "decision": "DISLIKE",
                "reasons": ["boring", "no_human_angle"],
            }
        )
    )
    result = CliRunner().invoke(app, ["review", "add", str(file), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    records = Pipeline(tmp_path).store.editorial_feedback("unseen")
    assert records[0].decision == "DISLIKE" and records[0].reasons[0] == "boring"
    with pytest.raises(ValueError):
        EditorialFeedback(candidate_id="unseen", decision="AUTO_PUBLISH", reasons=["x"])


def test_provider_cache_and_failure_isolation(config, lenses, store, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-a-real-secret")
    calls = []

    def handler(request):
        data = json.loads(request.content)
        calls.append(data["state"]["item"]["title"])
        if "unavailable" in data["state"]["item"]["title"]:
            return httpx.Response(503)
        return httpx.Response(200, json=response_for(data))

    items = [candidate(), candidate(id="fail", title="Provider unavailable item")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        judge = SemanticJudge(config, lenses, store, http)
        first = judge.assess(items)
        second = judge.assess([items[0]])
    assert first["unseen-case"][1] == "live" and second["unseen-case"][1] == "cache"
    assert len(calls) == 2
    assert first["fail"][1] == "unavailable"
    assert "test-key" not in first["fail"][2]
    assert (
        compose_assessment(items[1], None, config, lenses, mode="unavailable").editorial_value[
            "status"
        ]
        == "awaiting_review"
    )


def test_missing_credential_never_returns_fake_editorial_candidates(
    config, lenses, store, monkeypatch
):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    result = SemanticJudge(config, lenses, store).assess([candidate()])
    response, mode, error = result["unseen-case"]
    assessed = compose_assessment(candidate(), response, config, lenses, mode, error)
    assert assessed.editorial_score == 0
    assert select_screened([assessed], config, 5)[1] == []


def test_provider_cannot_invent_an_evidence_span(config, lenses):
    request = judgment_request(candidate(), config, lenses)
    data = response_for(request)
    data["answers"]["signal_person"]["choice"] = "an invented quotation"
    with pytest.raises(ValueError):
        validate_response(data, request)


def test_english_title_seed_is_rejected(style):
    with pytest.raises(ValueError):
        public_brief(candidate(editorial_title_seed="New AI worker tool"), style)
