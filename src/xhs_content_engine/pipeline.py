import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from .collectors import ADAPTERS, SkipSource, client, collect_manual, telegram_batch
from .editorial import export
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

    def rank(self, limit=20):
        return rank(self.store.items(), self.scoring, limit)

    def export(self, limit=20):
        return export(self.rank(limit), self.root / "outputs", self.style, datetime.now(UTC))

    def run(self, limit=20):
        report = self.collect()
        candidates = self.rank(limit)
        folder = export(candidates, self.root / "outputs", self.style, datetime.now(UTC))
        report.update(
            top_candidates=len(candidates),
            editorial_packets=len(candidates),
            public_briefs_checked=len(candidates),
            editorial_directory=str(folder),
        )
        (self.root / "outputs" / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report
