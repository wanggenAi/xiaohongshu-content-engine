"""Deterministic story discovery before semantic Human Trigger scoring.

This module copies or classifies source evidence only. It never invents a person,
result, conflict, trend, or comment. The local score controls cost and review order.
"""

import hashlib
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .models import ContentItem, StoryCandidate


def _text(item: ContentItem) -> str:
    return " ".join(
        part.strip() for part in (item.title, item.raw_excerpt, item.summary) if part.strip()
    )


def _terms(config: dict, key: str) -> list[str]:
    return [str(term).casefold() for term in config.get(key, [])]


def _has(text: str, terms: list[str]) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in terms)


def _spans(item: ContentItem) -> list[str]:
    spans = [item.title.strip()]
    if item.raw_excerpt.strip():
        spans.extend(
            part.strip()
            for part in re.split(r"(?<=[.!?。！？])\s+|\n+", item.raw_excerpt)
            if part.strip()
        )
    for value in (item.metadata.get("comments"), item.metadata.get("replies")):
        if isinstance(value, list):
            spans.extend(str(v).strip() for v in value if str(v).strip())
    return list(dict.fromkeys(spans))


def _discussion(item: ContentItem) -> list[dict]:
    raw = item.metadata.get("discussion_viewpoints", [])
    if not isinstance(raw, list):
        return []
    result = []
    for viewpoint in raw:
        if not isinstance(viewpoint, dict):
            continue
        evidence = str(viewpoint.get("evidence", "")).strip()
        if evidence:
            result.append(
                {
                    "stance": str(viewpoint.get("stance", "")).strip(),
                    "evidence": evidence,
                    "is_first_person": bool(viewpoint.get("is_first_person", False)),
                }
            )
    return result


def _identity_groups(text: str, config: dict) -> list[str]:
    lowered = text.casefold()
    return [
        identity
        for identity, terms in config.get("identity_terms", {}).items()
        if any(str(term).casefold() in lowered for term in terms)
    ]


def _first_person(text: str, config: dict) -> bool:
    lowered = text.casefold()
    for term in _terms(config, "first_person_terms"):
        if re.fullmatch(r"[a-z][a-z' ]*", term):
            if re.search(r"\b" + re.escape(term) + r"\b", lowered):
                return True
        elif term in lowered:
            return True
    return False


def _action_span(spans: list[str], config: dict) -> str:
    return next((span for span in spans if _has(span, _terms(config, "action_terms"))), "")


def _consequence_span(spans: list[str], config: dict) -> str:
    return next((span for span in spans if _has(span, _terms(config, "consequence_terms"))), "")


def _before_after(spans: list[str], config: dict) -> tuple[str, str]:
    terms = _terms(config, "before_after_terms")
    for span in spans:
        if not _has(span, terms):
            continue
        parts = re.split(
            r",?\s+(?:but|however|now|today|after|later|后来|现在|但|却|然而)\s+|，(?:但|却|后来|现在)",
            span,
            maxsplit=1,
            flags=re.I,
        )
        if len(parts) == 2 and all(part.strip() for part in parts):
            return parts[0].strip(), parts[1].strip()
        # A marker such as “now” is not enough: require two recoverable clauses.
        return "", ""
    return "", ""


def _conflict_span(spans: list[str], config: dict) -> str:
    return next((span for span in spans if _has(span, _terms(config, "conflict_terms"))), "")


def _number_signal(text: str) -> bool:
    return bool(
        re.search(
            r"(?<![\w])(?:\$|€|£)?\d[\d,.]*"
            r"(?:%| percent| people| users| employees|k|m|小时|天|人)?\b",
            text,
            re.I,
        )
    )


def _source_tier(item: ContentItem, source_priority: dict | None) -> str:
    if not source_priority:
        return "C"
    for tier, definition in source_priority.get("tiers", {}).items():
        if item.source_type in definition.get("source_types", []):
            return tier
    return source_priority.get("defaults", {}).get("unknown_tier", "C")


def fallback_story_score(
    item: ContentItem, config: dict, now: datetime | None = None
) -> tuple[float, dict[str, float]]:
    """Return a transparent triage score; this is never a Human Trigger score."""
    now = now or datetime.now(UTC)
    text = _text(item)
    spans = _spans(item)
    discussion = _discussion(item)
    before, after = _before_after(spans, config)
    first = _first_person(text, config)
    identity = bool(_identity_groups(text, config))
    action = bool(_action_span(spans, config))
    consequence = bool(_consequence_span(spans, config))
    comments = any(v["is_first_person"] for v in discussion)
    raw_comments = []
    for key in ("comments", "replies"):
        values = item.metadata.get(key)
        if isinstance(values, list):
            raw_comments.extend(str(value) for value in values)
    comments = comments or any(_first_person(value, config) for value in raw_comments)
    viewpoints = len({v["stance"] for v in discussion if v["stance"]}) >= 2
    evidence = len(spans) >= 2 or item.verification_state == "verified"
    fresh = bool(item.published_at and now - timedelta(days=7) <= item.published_at <= now)
    flags = {
        "first_person": float(first),
        "specific_identity": float(identity),
        "action_result_structure": float(action and consequence),
        "consequence_terms": float(consequence),
        "discussion_engagement": float(
            bool(item.engagement_metrics) or bool(discussion) or bool(raw_comments)
        ),
        "before_after_signal": float(bool(before and after)),
        "number_detail_density": float(_number_signal(text)),
        "source_freshness": float(fresh),
        "first_person_comments": float(comments),
        "multiple_viewpoints": float(viewpoints),
        "evidence_quality": float(evidence),
        "source_tier_s": float(_source_tier(item, config.get("source_priority")) == "S"),
    }
    weights = {
        "first_person": 20,
        "specific_identity": 15,
        "action_result_structure": 20,
        "consequence_terms": 15,
        "discussion_engagement": 10,
        "before_after_signal": 10,
        "number_detail_density": 5,
        "source_freshness": 5,
    }
    return round(sum(weights[key] * flags[key] for key in weights), 2), flags


def story_richness_score(item: ContentItem, config: dict, now: datetime | None = None) -> float:
    """Score the ten requested story dimensions independently of Human Trigger."""
    _, flags = fallback_story_score(item, config, now)
    text = _text(item)
    spans = _spans(item)
    action = bool(_action_span(spans, config))
    consequence = bool(_consequence_span(spans, config))
    dimensions = {
        "first_person": flags["first_person"],
        "concrete_actor": float(bool(item.author) or bool(_identity_groups(text, config))),
        "specific_action": float(action),
        "consequence": float(consequence),
        "before_after": flags["before_after_signal"],
        "conflict": float(bool(_conflict_span(spans, config))),
        "numbers": flags["number_detail_density"],
        "first_person_comments": flags["first_person_comments"],
        "multiple_viewpoints": flags["multiple_viewpoints"],
        "evidence_quality": flags["evidence_quality"],
    }
    weights = config.get("weights", {})
    return round(sum(dimensions[key] * weights.get(key, 0) for key in dimensions), 2)


def mine_story_candidate(
    item: ContentItem, config: dict, now: datetime | None = None
) -> StoryCandidate:
    now = now or datetime.now(UTC)
    spans = _spans(item)
    text = _text(item)
    discussion = _discussion(item)
    before, after = _before_after(spans, config)
    action = _action_span(spans, config)
    consequence = _consequence_span(spans, config)
    conflict = _conflict_span(spans, config)
    identities = _identity_groups(text, config)
    first = _first_person(text, config)
    fallback, _ = fallback_story_score(item, config, now)
    richness = story_richness_score(item, config, now)
    evidence = list(
        dict.fromkeys(
            [item.title, *[s for s in (action, consequence, before, after, conflict) if s]]
        )
    )
    person = (
        item.author if first and item.author else ("第一人称作者（需核实身份）" if first else "")
    )
    if not person and identities:
        person = identities[0]
    if not (person and action and consequence):
        story_type = "weak_news"
    elif before and after:
        story_type = "before_after"
    else:
        story_type = "single_case"
    return StoryCandidate(
        id=f"story-{item.id}",
        source_item_ids=[item.id],
        story_type=story_type,
        primary_person=person,
        identity_group=identities,
        action=action,
        context=item.title,
        before_state=before,
        change_event=action,
        after_state=after,
        result=consequence,
        conflict=conflict,
        surprise=conflict,
        money_signal=consequence if _has(text, ["$", "salary", "revenue", "收入", "工资"]) else "",
        job_signal=consequence if _has(text, ["job", "work", "career", "工作", "职位"]) else "",
        emotion_signal=consequence if _has(text, ["worry", "fear", "担心", "害怕"]) else "",
        evidence_spans=evidence,
        discussion_evidence=discussion,
        engagement=item.engagement_metrics,
        claim_scope="single_case",
        verification_state=item.verification_state,
        story_strength=richness,
        fallback_story_score=fallback,
        source_tier=_source_tier(item, config.get("source_priority")),
        source_authority=item.source_reliability,
        story_value=richness,
    )


def enrich_story_items(
    items: list[ContentItem],
    config: dict,
    source_priority: dict | None = None,
    now: datetime | None = None,
) -> tuple[list[ContentItem], list[StoryCandidate]]:
    now = now or datetime.now(UTC)
    config = {
        "fast_filter": {"minimum_score": 40, "limit": 50},
        "identity_terms": {},
        "action_terms": [],
        "consequence_terms": [],
        "before_after_terms": [],
        "conflict_terms": [],
        "first_person_terms": [],
        **config,
    }
    enriched, candidates = [], []
    local_config = {**config, "source_priority": source_priority or {}}
    for item in items:
        candidate = mine_story_candidate(item, local_config, now)
        copy = item.model_copy(deep=True)
        copy.story_richness_score = candidate.story_strength
        copy.fallback_story_score = candidate.fallback_story_score
        copy.story_structure = {
            "who": candidate.primary_person,
            "did_what": candidate.action,
            "change_event": candidate.change_event,
            "what_happened": candidate.result,
            "before_state": candidate.before_state,
            "after_state": candidate.after_state,
        }
        copy.story_conflict = candidate.conflict
        copy.discussion_viewpoints = candidate.discussion_evidence
        copy.story_mining_status = (
            "candidate"
            if candidate.story_strength >= config["fast_filter"]["minimum_score"]
            else "weak"
        )
        copy.metadata["story_mining"] = {
            "tier": _source_tier(copy, source_priority),
            "flags": fallback_story_score(copy, local_config, now)[1],
            "evidence_spans": candidate.evidence_spans,
        }
        enriched.append(copy)
        candidates.append(candidate)
    _assign_clusters(enriched, candidates)
    return enriched, candidates


def _assign_clusters(items: list[ContentItem], candidates: list[StoryCandidate]) -> None:
    buckets: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        tokens = re.findall(r"[a-z]{4,}|[\u4e00-\u9fff]{2,}", candidate.context.casefold())
        key = " ".join(sorted(set(tokens[:6])))
        if key:
            buckets[key].append(index)
    for key, indexes in buckets.items():
        if len(indexes) < 2:
            continue
        cluster_id = "cluster-" + hashlib.sha1(key.encode()).hexdigest()[:10]
        cases = [candidates[index].id for index in indexes]
        for index in indexes:
            candidates[index].story_cluster_id = cluster_id
            candidates[index].story_type = "multiple_cases"
            items[index].story_cluster_id = cluster_id
            items[index].story_cluster = {
                "theme": key,
                "independent_cases": cases,
                "shared_pattern": "",
                "conflicting_cases": [],
            }


def fast_story_filter(
    items: list[ContentItem], config: dict, limit: int | None = None
) -> list[ContentItem]:
    limit = limit or config.get("fast_filter", {}).get("limit", 50)
    threshold = config.get("fast_filter", {}).get("minimum_score", 40)
    eligible = [item for item in items if item.story_richness_score >= threshold]
    eligible.sort(
        key=lambda item: (-item.fallback_story_score, -item.story_richness_score, item.id)
    )
    if not eligible and items:
        # Preserve one reviewable sample during an outage; its weak signal stays visible.
        eligible = sorted(items, key=lambda item: (-item.fallback_story_score, item.id))[:1]
    return eligible[:limit]


def story_semantic_filter(items: list[ContentItem], config: dict) -> list[ContentItem]:
    """Bound the expensive downstream semantic pass to the strongest story inputs."""
    fast = fast_story_filter(items, config)
    maximum = config.get("fast_filter", {}).get("maximum_semantic_candidates", 20)
    minimum = config.get("fast_filter", {}).get("minimum_semantic_candidates", 10)
    # Keep a useful minimum when the feed is small, while never exceeding the cap.
    return fast[: max(minimum, min(maximum, len(fast)))]


def story_queries(config: dict) -> list[str]:
    """Return configured search combinations without embedding provider-specific queries."""
    return list(dict.fromkeys(config.get("story_queries", [])))
