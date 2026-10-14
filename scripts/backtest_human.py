"""Replay eight frozen real candidates and six explicitly synthetic policy fixtures.

Run with `uv run python scripts/backtest_human.py`. Requires TYPESAFE_API_KEY for
live evaluation; cached judgments are reused only when evidence/rubrics match.
Never ingests synthetic fixtures into the production candidate store.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from xhs_content_engine.editorial_screening import SemanticJudge, compose_assessment
from xhs_content_engine.human_triggers import HumanJudge, compose_human
from xhs_content_engine.models import ContentItem
from xhs_content_engine.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def main():
    pipeline = Pipeline(ROOT)
    actual = [
        ContentItem.model_validate(row)
        for row in json.loads((ROOT / "tests/fixtures/v12_real_candidates.json").read_text())
    ]
    fixtures = json.loads((ROOT / "tests/fixtures/human_trigger_cases.json").read_text())
    synthetic = [
        ContentItem(
            id="fixture-" + row["id"],
            source="SYNTHETIC_TEST_ONLY",
            source_type="manual",
            canonical_url="https://example.org/fixture/" + row["id"],
            title=row["title"],
            raw_excerpt=row["raw_excerpt"],
            published_at=datetime(2026, 10, 14, tzinfo=UTC),
        )
        for row in fixtures
    ]
    items = actual + synthetic
    editorial = SemanticJudge(pipeline.editorial_scoring, pipeline.lenses, pipeline.store).assess(
        items
    )
    human = HumanJudge(pipeline.editorial_scoring, pipeline.human_config, pipeline.store).assess(
        items
    )
    assessed = []
    for item in items:
        response, mode, error = editorial[item.id]
        a = compose_assessment(
            item, response, pipeline.editorial_scoring, pipeline.lenses, mode, error
        )
        response, mode, error = human[item.id]
        assessed.append(compose_human(a, response, pipeline.human_config, mode, error))
    result = {
        "real_candidates": [i.model_dump(mode="json") for i in assessed[: len(actual)]],
        "synthetic_fixtures": [i.model_dump(mode="json") for i in assessed[len(actual) :]],
        "expectations": {row["id"]: row["expected"] for row in fixtures},
    }
    destination = ROOT / "outputs/v12_backtest.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if any(item.semantic_status != "assessed" for item in assessed):
        raise RuntimeError(
            "Incomplete semantic backtest; see raw responses, do not claim quality acceptance"
        )
    for item, fixture in zip(assessed[len(actual) :], fixtures, strict=True):
        if fixture["expected"] == "low":
            assert (
                item.human_trigger_score < 30
                and "LOW_HUMAN_TRIGGER" in item.editorial_reject_reason
            ), fixture["id"]
        else:
            assert item.human_trigger_score >= 65, fixture["id"]
    assert assessed[2].human_trigger_score > assessed[3].human_trigger_score, (
        "Bot scene must outrank unsupported B2B security stakes"
    )
    for item in assessed:
        print(
            json.dumps(
                {
                    "id": item.id,
                    "title": item.title,
                    "editorial": item.editorial_score,
                    "human": item.human_trigger_score,
                    "viral": item.viral_potential,
                    "triggers": item.strongest_triggers,
                    "gate": item.human_trigger_breakdown.get("gate"),
                    "reject": item.editorial_reject_reason,
                    "scene": item.human_trigger_breakdown.get("strong_scene"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
