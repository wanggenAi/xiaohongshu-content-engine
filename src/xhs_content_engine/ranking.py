import hashlib
import math
import re
from datetime import UTC, datetime

from .models import ContentItem


def dedupe(items: list[ContentItem]) -> list[ContentItem]:
    """Exact URL and conservative exact long-title matches; preserve every internal source."""
    parent = list(range(len(items)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    seen = {}
    for index, item in enumerate(items):
        keys = ["url:" + item.canonical_url]
        title = re.sub(r"\W+", " ", item.title.casefold()).strip()
        if len(title) >= 40:
            keys.append("title:" + title)
        for key in keys:
            if key in seen:
                parent[root(index)] = root(seen[key])
            seen[key] = index
    groups = {}
    for index, item in enumerate(items):
        groups.setdefault(root(index), []).append(item)
    unique = []
    for group in groups.values():
        best = max(group, key=lambda item: (item.source_reliability, bool(item.raw_excerpt)))
        best = best.model_copy(deep=True)
        best.duplicate_group = hashlib.sha256(
            min(item.canonical_url for item in group).encode()
        ).hexdigest()[:16]
        best.metadata["provenance"] = [
            dict(
                source=i.source,
                source_type=i.source_type,
                canonical_url=i.canonical_url,
                original_url=i.metadata.get("original_url", i.canonical_url),
                author=i.author,
                published_at=i.published_at.isoformat() if i.published_at else None,
                engagement_metrics=i.engagement_metrics,
                observed_at=i.fetched_at.isoformat(),
            )
            for i in group
        ]
        best.metadata["duplicate_count"] = len(group) - 1
        unique.append(best)
    return unique


def score(item: ContentItem, config: dict, now: datetime | None = None) -> ContentItem:
    now = now or datetime.now(UTC)
    age_hours = (
        max(0, (now - item.published_at).total_seconds() / 3600) if item.published_at else None
    )
    text = f"{item.title} {item.raw_excerpt} {' '.join(item.tags)}".casefold()

    def keyword_value(dimension):
        hits = [
            k
            for k in config["keywords"][dimension]
            if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", text)
        ]
        return min(1, len(hits) / 3), hits

    evidence = {}
    dimensions = {}
    for key in config["keywords"]:
        dimensions[key], evidence[key] = keyword_value(key)
    dimensions["freshness"] = (
        0 if age_hours is None else 2 ** (-age_hours / config.get("freshness_half_life_hours", 48))
    )
    metrics = item.engagement_metrics
    # Platform scales differ. This is interest evidence, not a momentum estimate.
    if item.source_type.startswith("github"):
        count, ceiling = metrics.get("stars", 0), 1000
    elif item.source_type == "hacker_news":
        count, ceiling = metrics.get("points", 0) + metrics.get("comments", 0), 500
    else:
        count, ceiling = 0, 500
    dimensions["engagement"] = min(1, math.log1p(count) / math.log1p(ceiling))
    if metrics.get("comments", 0) >= 50:
        dimensions["discussion"] = max(dimensions["discussion"], 0.6)
        evidence["discussion"].append("at least 50 measured comments")
    dimensions["authority"] = item.source_reliability
    flags = set(item.metadata.get("flags", []))
    if item.verification_state != "verified":
        flags.add("unverified")
    if age_hours is not None and age_hours > config.get("max_age_days", 7) * 24:
        flags.add("stale")
    if not item.author and not item.raw_excerpt:
        flags.add("unclear_source")
    weighted = {key: round(value * config["weights"][key], 3) for key, value in dimensions.items()}
    penalties = {
        flag: config["penalties"][flag] for flag in sorted(flags) if flag in config["penalties"]
    }
    total = round(max(0, min(100, sum(weighted.values()) - sum(penalties.values()))), 2)
    return item.model_copy(
        update={
            "score": total,
            "score_breakdown": {
                "dimensions": dimensions,
                "weighted": weighted,
                "penalties": penalties,
                "keyword_evidence": evidence,
                "age_hours": age_hours,
                "method": "heuristic-v1; relevance and novelty are review signals, not facts",
                "unknown": [
                    "中文报道饱和度",
                    "独立事实核验",
                    "历史增长速度",
                    "标题党/广告人工判定",
                ],
            },
        }
    )


def rank(items: list[ContentItem], config: dict, limit=20, now: datetime | None = None):
    now = now or datetime.now(UTC)
    scored = [score(item, config, now) for item in dedupe(items)]
    scored.sort(key=lambda item: (-item.score, item.id))
    counts_source, counts_type, selected = {}, {}, []
    for item in scored:
        # Missing publication dates stay in the DB but cannot masquerade as fresh news.
        if (
            item.published_at is None
            or (now - item.published_at).total_seconds() > config["max_age_days"] * 86400
        ):
            continue
        if item.published_at > now or item.score <= 0:
            continue
        if counts_source.get(item.source, 0) >= config.get("max_per_source", 5):
            continue
        if counts_type.get(item.content_type, 0) >= config.get("max_per_content_type", 7):
            continue
        counts_source[item.source] = counts_source.get(item.source, 0) + 1
        counts_type[item.content_type] = counts_type.get(item.content_type, 0) + 1
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected
