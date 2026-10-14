import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from .collectors import ADAPTERS, SkipSource, client, collect_manual, telegram_batch
from .editorial import export, verify_outputs
from .editorial_screening import screen
from .human_triggers import human_review_queue
from .normalize import normalize
from .ranking import dedupe, rank
from .storage import Store


class Pipeline:
    def __init__(self, root: Path):
        self.root = root
        self.store = Store(root / "data" / "content.sqlite3")
        self.sources = self.load("sources.yaml")
        self.scoring = self.load("scoring.yaml")
        self.style = self.load("editorial_style.yaml")
        self.editorial_scoring = self.load("editorial_scoring.yaml")
        self.human_config = self.load("human_triggers.yaml")
        self.story_config = self.load("story_mining.yaml")
        self.source_priority = self.load("source_priority.yaml")
        self.reader_identities = self.load("reader_identities.yaml")
        self.editorial_scoring["human_triggers"] = self.human_config
        self.editorial_scoring["story_mining"] = self.story_config
        self.editorial_scoring["source_priority"] = self.source_priority
        if sum(self.human_config["weights"].values()) != 100:
            raise ValueError("human trigger weights must total 100")
        if abs(sum(self.human_config["viral_weights"].values()) - 1) > 0.001:
            raise ValueError("viral weights must total 1")
        self.review_queue = []
        self.lenses = self.load("editorial_lenses.yaml")["lenses"]
        if sum(self.editorial_scoring["weights"].values()) != 100:
            raise ValueError("editorial scoring weights must total 100")
        if abs(sum(self.scoring["weights"].values()) - 100) > 0.001:
            raise ValueError("scoring weights must total 100")
        if any(v < 0 for v in self.scoring["weights"].values()):
            raise ValueError("scoring weights must be nonnegative")

    def load(self, name):
        return yaml.safe_load((self.root / "config" / name).read_text(encoding="utf-8"))

    def save_raw(self, raw):
        items, errors = [], 0
        for row in raw:
            try:
                items.append(normalize(row, self.style["public_labels"]))
            except (ValueError, TypeError, KeyError):
                errors += 1
        return items, errors

    def collect(self, http=None):
        now = datetime.now(UTC)
        owned = http is None
        http = http or client()
        audit, raw_count, collected = [], 0, []
        try:
            sources = [*self.sources.get("sources", []), {"name": "manual_inbox", "type": "manual"}]
            for config in sources:
                row = {"source": config["name"], "status": "ok", "raw_items": 0, "saved_items": 0}
                try:
                    if not config.get("enabled", True):
                        raise SkipSource("disabled by config")
                    if config["type"] == "restricted_adapter":
                        raise SkipSource(config["reason"])
                    if config["type"] == "telegram_bot":
                        rejected = 0
                        for _ in range(config.get("max_batches", 5)):
                            offset = self.store.get_state("telegram_offset", 0)
                            raw, next_offset, size, ignored = telegram_batch(config, http, offset)
                            items, invalid = self.save_raw(raw)
                            # Invalid records prevent acknowledgement to avoid silent data loss.
                            if invalid:
                                raise ValueError("invalid Telegram record; offset not advanced")
                            self.store.save_batch(items, {"telegram_offset": next_offset})
                            collected.extend(items)
                            row["raw_items"] += len(raw)
                            row["saved_items"] += len(items)
                            rejected += ignored
                            if size < 100:
                                break
                        row["rejected_messages"] = rejected
                    else:
                        if config["type"] == "manual":
                            raw, details = collect_manual(self.store.inbox()), {}
                        else:
                            raw, details = ADAPTERS[config["type"]](config, http)
                        row["raw_items"] = len(raw)
                        items, errors = self.save_raw(raw)
                        row.update(details, saved_items=len(items), normalization_errors=errors)
                        self.store.save_batch(items)
                        collected.extend(items)
                    if row.get("item_errors", 0) or row.get("normalization_errors", 0):
                        row["status"] = "partial"
                    if row["raw_items"] == 0:
                        row["status"] = "empty"
                except SkipSource as exc:
                    row.update(status="skip", reason=str(exc))
                except Exception as exc:
                    # HTTP errors embed request URLs (Telegram tokens). Log only class/status.
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    row.update(status="error", reason=type(exc).__name__, http_status=status)
                raw_count += row["raw_items"]
                audit.append(row)
        finally:
            if owned:
                http.close()
        self.store.prune((now - timedelta(days=30)).isoformat())
        items = self.store.items()
        report = {
            "run_at": now.isoformat(),
            "raw_items_this_run": raw_count,
            "unique_items_this_run": len(dedupe(collected)),
            "stored_items": len(items),
            "unique_items": len(dedupe(items)),
            "sources": audit,
        }
        destination = self.root / "outputs"
        destination.mkdir(exist_ok=True)
        (destination / "collection_audit.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report

    def screen(self, limit=10, http=None):
        assessed, stage_b, deep, report = screen(
            self.store.items(),
            self.scoring,
            self.editorial_scoring,
            self.lenses,
            self.store,
            limit=limit,
            http=http,
        )
        self.store.save_assessments(assessed)
        self.review_queue = human_review_queue(assessed, deep, self.human_config, limit)
        destination = self.root / "outputs"
        destination.mkdir(exist_ok=True)
        (destination / "editorial_screening.json").write_text(
            json.dumps(
                {
                    **report,
                    "assessments": [i.model_dump(mode="json") for i in assessed],
                    "stage_b_ids": [i.id for i in stage_b],
                    "deep_candidate_ids": [i.id for i in deep],
                    "human_review_queue_items": [
                        i.model_dump(mode="json") for i in self.review_queue
                    ],
                    "story_candidates": report.get("story_candidates_data", []),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        story_candidates = report.pop("story_candidates_data", [])
        (destination / "story_candidates.json").write_text(
            json.dumps(story_candidates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return deep, report

    def rank(self, limit=10):
        return self.screen(limit)[0]

    def export(self, limit=10):
        candidates, funnel = self.screen(limit)
        folder = export(
            candidates, self.root / "outputs", self.style, datetime.now(UTC), self.review_queue
        )
        audit_file = self.root / "outputs" / "collection_audit.json"
        report = json.loads(audit_file.read_text()) if audit_file.exists() else {}
        report.update(
            funnel,
            operation="export",
            exported_at=datetime.now(UTC).isoformat(),
            top_candidates=len(candidates),
            editorial_packets=len(candidates),
            public_briefs_checked=len(candidates),
            human_review_packets=len(self.review_queue),
            editorial_directory=str(folder),
        )
        (self.root / "outputs" / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        verify_outputs(self.root / "outputs", self.style, report)
        return folder

    def run(self, limit=10):
        report = self.collect()
        # Retain a V1 ranking of the same current evidence for comparisons.
        old = rank(self.store.items(), self.scoring, 20)
        (self.root / "outputs" / "discovery_top20.json").write_text(
            json.dumps([i.model_dump(mode="json") for i in old], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        candidates, funnel = self.screen(limit)
        folder = export(
            candidates, self.root / "outputs", self.style, datetime.now(UTC), self.review_queue
        )
        report.update(
            funnel,
            top_candidates=len(candidates),
            editorial_packets=len(candidates),
            public_briefs_checked=len(candidates),
            human_review_packets=len(self.review_queue),
            editorial_directory=str(folder),
        )
        (self.root / "outputs" / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        verify_outputs(self.root / "outputs", self.style, report)
        return report
