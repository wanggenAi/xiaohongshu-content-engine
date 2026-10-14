import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml

from xhs_content_engine.editorial import export, verify_outputs
from xhs_content_engine.editorial_screening import validate_response
from xhs_content_engine.human_triggers import (
    HumanJudge,
    compose_human,
    human_request,
    human_review_queue,
    human_spans,
)
from xhs_content_engine.models import ContentItem, EditorialFeedback
from xhs_content_engine.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 14, tzinfo=UTC)


@pytest.fixture
def config():
    return yaml.safe_load((ROOT / "config/human_triggers.yaml").read_text())


def item(**updates):
    return ContentItem(
        **(
            dict(
                id="worker",
                source="original",
                source_type="manual",
                canonical_url="https://example.org/worker",
                published_at=NOW,
                score=40,
                title=(
                    "A junior developer expected faster work, "
                    "but he worries he is losing basic skills"
                ),
                raw_excerpt=(
                    "A junior developer generates code with AI. "
                    "He worries about his own basic skills."
                ),
                editorial_score=65,
                editorial_title_seed="代码完成得更快，自己的基本功还在吗？",
                editorial_value={"status": "assessed", "lens": "junior_careers"},
                editorial_score_breakdown={
                    "dimensions": {"evidence_quality": 0.5, "story_strength": 0.8},
                    "weighted": {"story_strength": 12},
                },
            )
            | updates
        )
    )


def judgments(
    source,
    config,
    values=None,
    *,
    scene=True,
    identity="developers",
    scope="single_case",
    routes=True,
    reversal=True,
    anchors=True,
):
    request = human_request(source, config, "test")
    values = values or {key: 0.8 for key in config["weights"]}
    spans = human_spans(source)
    first, last = next(iter(spans)), next(reversed(spans))
    answers = {}
    for key, question in request["questions"].items():
        if question["type"] == "score":
            score = values.get(key.removeprefix("trigger_"), 0) * 3
            lo, hi = int(score), min(3, int(score) + 1)
            probs = {str(i): 0.0 for i in range(4)}
            probs[str(lo)] += 1 - (score - lo)
            probs[str(hi)] += score - lo
            answers[key] = dict(type="score", score=score, confidence=1, probabilities=probs)
        elif question["type"] == "noul":
            answers[key] = dict(type="noul", noul=float(routes))
        else:
            choice = first
            if key == "identity":
                choice = identity
            elif key == "scope":
                choice = scope
            elif key.startswith("anchor_") and not anchors:
                choice = "NONE"
            elif key.startswith("scene_") and not scene:
                choice = "NONE"
            elif key.startswith("reversal_"):
                choice = (first if key.endswith("setup") else last) if reversal else "NONE"
            answers[key] = dict(
                type="choice",
                choice=choice,
                confidence=1,
                probabilities={k: float(k == choice) for k in question["criteria"]},
            )
    return validate_response({"model": "test", "answers": answers}, request)


def assess(config, values=None, source=None, **kwargs):
    source = source or item()
    return compose_human(source, judgments(source, config, values, **kwargs), config)


def test_three_separate_scores_and_viral_weights(config):
    source = item()
    result = assess(config, source=source)
    assert result.discovery_score == source.discovery_score
    assert result.editorial_score == source.editorial_score
    assert 0 <= result.human_trigger_score <= 100
    assert result.viral_potential == round(
        result.human_trigger_score * 0.55 + 65 * 0.30 + 50 * 0.15, 2
    )
    assert sum(config["weights"].values()) == 100
    assert config["viral_weights"]["human_trigger"] > max(
        config["viral_weights"][k] for k in ("editorial", "evidence")
    )


@pytest.mark.parametrize("dimension", ["reversal", "scene", "identity", "money", "job_survival"])
def test_supported_trigger_boosts_priority(config, dimension):
    low = {k: 0.2 for k in config["weights"]}
    high = {**low, dimension: 1}
    assert assess(config, high).human_trigger_score > assess(config, low).human_trigger_score
    assert assess(config, high).viral_potential > assess(config, low).viral_potential


def test_no_scene_penalty_and_story_strength_cap(config):
    result = assess(config, scene=False)
    assert not any(result.scene.values())
    assert result.human_trigger_breakdown["multiplier"] == config["no_scene_multiplier"]
    assert result.editorial_score_breakdown["dimensions"]["story_strength"] == 0.25
    assert result.editorial_score < 65
    assert result.human_trigger_score < assess(config).human_trigger_score


def test_unsupported_high_scores_do_not_manufacture_human_stakes(config):
    result = assess(
        config, anchors=False, scene=False, identity="NONE", routes=False, reversal=False
    )
    assert result.human_trigger_score < 30
    assert result.human_trigger_breakdown["gate"] is None
    assert "LOW_HUMAN_TRIGGER" in result.editorial_reject_reason
    assert all(not v["evidence"] for v in result.human_trigger_map.values())


@pytest.mark.parametrize(
    "case",
    json.loads((ROOT / "tests/fixtures/human_trigger_cases.json").read_text()),
    ids=lambda c: c["id"],
)
def test_positive_and_negative_fixture_policy(config, case):
    # Controlled judgments test policy. The same texts receive live semantic
    # judgments in scripts/backtest_human.py, reported separately from pytest.
    source = item(id=case["id"], title=case["title"], raw_excerpt=case["raw_excerpt"])
    high = case["expected"] == "high"
    values = {key: 0.9 if high else 0.1 for key in config["weights"]}
    result = assess(
        config,
        values,
        source,
        scene=high,
        identity="developers" if high else "NONE",
        reversal=high,
        routes=high,
        anchors=high,
    )
    if high:
        assert result.human_trigger_score >= 65
    else:
        assert result.human_trigger_score < 30
        assert "LOW_HUMAN_TRIGGER" in result.editorial_reject_reason


@pytest.mark.parametrize("scope", ["single_case", "company_claim", "reported_trend"])
def test_claim_scope_and_three_distinct_non_exaggerated_seeds(config, scope):
    result = assess(config, scope=scope)
    assert result.claim_scope == scope
    assert len(result.human_title_seeds) == 3
    assert len({s["text"] for s in result.human_title_seeds}) == 3
    assert {s["angle"] for s in result.human_title_seeds} == {
        "scene",
        "reversal",
        "identity_interest",
    }
    assert all(s["claim_scope"] == scope for s in result.human_title_seeds)
    text = "".join(s["text"] for s in result.human_title_seeds)
    assert all(
        word not in text
        for word in ["已经裁员", "国外都在讨论", "所有程序员", "一定失业", "全行业"]
    )
    assert all(s["text"].endswith("？") for s in result.human_title_seeds)


@pytest.mark.parametrize("scope", ["verified_event", "multiple_sources"])
def test_scope_cannot_claim_unprovided_verification(config, scope):
    assert assess(config, scope=scope).claim_scope == "single_case"


def test_reader_projection_and_comment_routes(config):
    result = assess(config)
    assert "程序员" in result.reader_self_projection
    assert "假设" in result.reader_self_projection
    assert result.likely_comment_routes
    assert result.human_trigger_map["commentability"]["natural_question"]
    assert not assess(config, routes=False).likely_comment_routes
    assert assess(config, routes=False).human_trigger_score < result.human_trigger_score


def test_all_evidence_is_verbatim_and_reversal_has_two_different_parts(config):
    source = item()
    result = assess(config, source=source)
    spans = set(human_spans(source).values())
    assert all(v in spans for v in result.scene.values() if v)
    assert all(v in spans for v in result.reversal.values())
    assert result.reversal["setup"] != result.reversal["turn"]
    assert all(q in spans for t in result.human_trigger_map.values() for q in t["evidence"])


def test_missing_semantics_produces_honest_queue(config):
    source = item()
    result = compose_human(source, None, config, "unavailable", "LookupError:None")
    queue = human_review_queue([result], [], config)
    assert len(queue) == 1
    assert queue[0].semantic_status == "unavailable"
    assert queue[0].editorial_verdict == "NEEDS_HUMAN_REVIEW"
    assert queue[0].human_trigger_score is queue[0].viral_potential is None
    assert not queue[0].human_title_seeds


@pytest.mark.parametrize("decision", ["LIKE", "MAYBE", "DISLIKE"])
def test_feedback_compatible_with_new_reason_codes(decision):
    reasons = [
        "strong_reversal",
        "strong_identity",
        "strong_scene",
        "strong_money",
        "strong_job_angle",
        "strong_fear",
        "strong_desire",
        "strong_fairness",
        "too_news_like",
        "too_technical",
        "no_human_tension",
        "no_scene",
        "boring",
        "corporate_pr",
        "weak_evidence",
    ]
    assert (
        EditorialFeedback(candidate_id="worker", decision=decision, reasons=reasons).reasons
        == reasons
    )


def test_full_pipeline_without_api_still_exports_reviewable_queue(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    pipeline = Pipeline(tmp_path)
    pipeline.store.add_inbox(
        "https://example.org/worker",
        title="A developer says AI changed his work",
        note="One developer now reviews generated code and worries about basic skills.",
        published_at=datetime.now(UTC).isoformat(),
    )
    pipeline.sources = {"sources": []}
    report = pipeline.run()
    assert report["raw_items_this_run"] == 1
    assert report["deep_candidates"] == 0
    assert report["human_review_queue"] == 1
    review = (tmp_path / "outputs/editorial_review.md").read_text()
    assert "NEEDS_HUMAN_REVIEW" in review and "unavailable" in review
    assert "A developer says AI changed his work" in review
    assert verify_outputs(tmp_path / "outputs", pipeline.style, report)["human_review_queue"] == 1
    queue = json.loads((tmp_path / "outputs/human_review_queue.json").read_text())
    assert queue[0]["human_trigger_score"] is None


@pytest.mark.parametrize("corrupt", ["heading", "table", "json", "packet", "report"])
def test_report_count_consistency_detects_real_file_mismatches(tmp_path, config, corrupt):
    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    export([assess(config)], tmp_path, style, NOW)
    if corrupt == "heading":
        p = tmp_path / "editorial_review.md"
        p.write_text(p.read_text().replace("Deep Candidates：1", "Deep Candidates：8"))
    elif corrupt == "table":
        p = tmp_path / "editorial_review.md"
        p.write_text(p.read_text().replace("| 1 |", "| 9 |\n| 2 |"))
    elif corrupt == "json":
        (tmp_path / "top_candidates.json").write_text("[]")
    elif corrupt == "packet":
        next((tmp_path / "editorial").rglob("*.md")).unlink()
    report = {"deep_candidates": 8} if corrupt == "report" else None
    with pytest.raises(ValueError):
        verify_outputs(tmp_path, style, report)


def test_provider_timeout_and_mixed_outage_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-not-secret")
    shutil.copytree(ROOT / "config", tmp_path / "config")
    pipeline = Pipeline(tmp_path)

    def handler(request):
        raise httpx.ReadTimeout("timeout")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        result = HumanJudge(
            pipeline.editorial_scoring, pipeline.human_config, pipeline.store, http
        ).assess([item()])
    response, mode, error = result["worker"]
    pending = compose_human(item(), response, pipeline.human_config, mode, error)
    assert human_review_queue([pending], [], pipeline.human_config)


def test_same_sentence_reversal_recovers_only_verbatim_clauses(config):
    from xhs_content_engine.human_triggers import extract_reversal

    source = item(title="The owner expected readers, but logs showed automated clients")
    request = human_request(source, config, "test")
    response = judgments(source, config)
    for key in ("reversal_setup", "reversal_turn"):
        answer = response.answers[key]
        answer.choice = "s0"
        answer.probabilities = {
            option: float(option == "s0") for option in request["questions"][key]["criteria"]
        }
    reversal = extract_reversal(response.answers, human_spans(source), 0.65)
    assert reversal == {
        "setup": "The owner expected readers",
        "turn": "logs showed automated clients",
    }
    assert all(text in source.title for text in reversal.values())


def test_title_questions_keep_verbatim_source_anchor(config):
    source = item()
    result = assess(config, source=source)
    for seed in result.human_title_seeds:
        assert seed["evidence_anchor"] in set(human_spans(source).values())
        assert seed["status"] == "investigation_question"
    bot = assess(
        config, source=item(editorial_value={"status": "assessed", "lens": "automated_attention"})
    )
    assert "检查之后" not in bot.human_title_seeds[0]["text"]


def test_deep_sorting_prefers_human_tension_over_high_editorial_score(config):
    from xhs_content_engine.editorial_screening import select_screened

    editorial = yaml.safe_load((ROOT / "config/editorial_scoring.yaml").read_text())
    editorial["human_triggers"] = config
    dims = {
        "evidence_quality": 0.5,
        "story_strength": 0.8,
        "human_relevance": 0.8,
        "china_audience_relevance": 0.8,
    }
    source = item(
        editorial_score_breakdown={"dimensions": dims, "weighted": {"story_strength": 12}}
    )
    human = assess(config, source=source)
    news = human.model_copy(deep=True)
    news.id, news.editorial_score = "news", 90
    news.human_trigger_score, news.viral_potential = 20, 45
    news.human_trigger_breakdown["gate"] = None
    news.editorial_reject_reason = ["LOW_HUMAN_TRIGGER"]
    stage_b, deep = select_screened([news, human], editorial, 5)
    assert len(stage_b) == 2
    assert deep == [human]


def test_rejected_batch_retains_manual_audit_without_promoting_it(config):
    weak = assess(
        config,
        {key: 0.1 for key in config["weights"]},
        scene=False,
        identity="NONE",
        routes=False,
        reversal=False,
        anchors=False,
    )
    queue = human_review_queue([weak], [], config)
    assert len(queue) == 1
    assert queue[0].editorial_verdict == "NEEDS_HUMAN_REVIEW"
    assert "LOW_HUMAN_TRIGGER" in queue[0].editorial_reject_reason
    assert queue[0].semantic_status == "assessed"


def test_provider_failure_clears_old_human_claims(config):
    old = assess(config)
    unavailable = compose_human(old, None, config, "unavailable")
    assert unavailable.semantic_status == "unavailable"
    assert not unavailable.scene and not unavailable.reversal
    assert not unavailable.human_title_seeds
    assert not unavailable.reader_self_projection
    assert unavailable.claim_scope == "unassessed"


def test_markdown_alias_mismatch_is_rejected(tmp_path, config):
    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    export([assess(config)], tmp_path, style, NOW)
    (tmp_path / "top_candidates.md").write_text("Top 8: stale report")
    with pytest.raises(ValueError, match="alias"):
        verify_outputs(tmp_path, style)


def test_export_after_run_refreshes_counts_instead_of_leaving_old_report(tmp_path, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    shutil.copytree(ROOT / "config", tmp_path / "config")
    pipeline = Pipeline(tmp_path)
    pipeline.sources = {"sources": []}
    for index in range(2):
        pipeline.store.add_inbox(
            f"https://example.org/story-{index}",
            title=f"AI changes a developer work task {index}",
            note="One worker reports changed code review tasks and learning concerns.",
            published_at=datetime.now(UTC).isoformat(),
        )
    assert pipeline.run(limit=1)["human_review_queue"] == 1
    pipeline.export(limit=2)
    report = json.loads((tmp_path / "outputs/run_report.json").read_text())
    assert report["human_review_queue"] == 2
    verify_outputs(tmp_path / "outputs", pipeline.style, report)


def test_unavailable_packet_never_displays_fake_zero_score_or_scene_judgment(config):
    from xhs_content_engine.editorial import packet
    from xhs_content_engine.editorial_screening import compose_assessment

    editorial = yaml.safe_load((ROOT / "config/editorial_scoring.yaml").read_text())
    lenses = yaml.safe_load((ROOT / "config/editorial_lenses.yaml").read_text())["lenses"]
    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    pending = compose_assessment(item(), None, editorial, lenses, "unavailable")
    pending = compose_human(pending, None, config, "unavailable")
    text = packet(human_review_queue([pending], [], config)[0], style)
    assert "编辑价值：未评估" in text
    assert "编辑价值：0.00" not in text
    assert "WEAK_EVIDENCE" not in text
    assert "NO STRONG SCENE FOUND" not in text


def test_unavailable_queue_preserves_discovery_priority_and_evidence_tiebreak(config):
    high = compose_human(item(id="high", score=50, raw_excerpt=""), None, config, "unavailable")
    low = compose_human(item(id="low", score=20), None, config, "unavailable")
    assert human_review_queue([low, high], [], config)[0].id == "high"
    equal = compose_human(item(id="equal", score=50), None, config, "unavailable")
    assert human_review_queue([high, equal], [], config)[0].id == "equal"


def test_unavailable_queue_can_show_verbatim_clause_without_platform_leak(config):
    from xhs_content_engine.editorial import queue_evidence, validate_public

    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    source = item(
        title="I posted to HN, and then my website was flooded with AI bot traffic", raw_excerpt=""
    )
    quote = queue_evidence(source, style)
    assert "my website was flooded with AI bot traffic" in quote
    assert "原文片段" in quote
    validate_public(quote, style)


def test_failed_batch_opens_circuit_instead_of_waiting_for_all_items(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-not-secret")
    shutil.copytree(ROOT / "config", tmp_path / "config")
    pipeline = Pipeline(tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    items = [item(id=str(index), title=f"Worker account {index}") for index in range(15)]
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        results = HumanJudge(
            pipeline.editorial_scoring, pipeline.human_config, pipeline.store, http
        ).assess(items)
    assert len(calls) == pipeline.editorial_scoring["provider"]["concurrency"]
    assert len(results) == len(items)
    assert all(v[1] == "unavailable" for v in results.values())
    assert sum(v[2] == "ProviderCircuitOpen:not_attempted" for v in results.values()) == 12


def test_budget_expiry_keeps_successful_judgment_and_queues_remaining(
    tmp_path, config, monkeypatch
):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    pipeline = Pipeline(tmp_path)
    pipeline.editorial_scoring["provider"].update(concurrency=1, budget_seconds=1)
    clock = [0]
    monkeypatch.setattr("xhs_content_engine.editorial_screening.monotonic", lambda: clock[0])
    items = [item(id=str(index), title=item().title + f" ({index})") for index in range(4)]
    judge = HumanJudge(pipeline.editorial_scoring, config, pipeline.store)

    def fetch(request):
        clock[0] = 2
        return judgments(items[0], config).model_dump(mode="json")

    monkeypatch.setattr(judge, "fetch", fetch)
    results = judge.assess(items)
    assert results["0"][1] == "live"
    assert all(
        results[str(index)][2] == "ProviderBudgetExhausted:not_attempted" for index in range(1, 4)
    )
