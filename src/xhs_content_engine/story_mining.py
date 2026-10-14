"""Deterministic story discovery before semantic Human Trigger scoring.

This module copies or classifies source evidence only. It never invents a person,
result, conflict, trend, or comment. The local score controls cost and review order.
"""

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .editorial_screening import POLICY, SemanticJudge, evidence_spans
from .models import ContentItem, StoryCandidate


def _text(item: ContentItem) -> str:
    return " ".join(
        part.strip() for part in (item.title, item.raw_excerpt, item.summary) if part.strip()
    )


def _terms(config: dict, key: str) -> list[str]:
    return [str(term).casefold() for term in config.get(key, [])]


def _has(text: str, terms: list[str]) -> bool:
    lowered = text.casefold()
    return any(
        bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", lowered))
        if re.search(r"[a-z]", term)
        else term in lowered
        for term in terms
    )


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
        if _has(lowered, [str(term).casefold() for term in terms])
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
    if item.metadata.get("source_tier") in {"S", "A", "B", "C"}:
        return item.metadata["source_tier"]
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
    public_comments = item.metadata.get("discussion_comments", [])
    comment_texts = [str(c.get("evidence", "")) for c in public_comments]
    discussion = _discussion(item)
    before, after = _before_after(spans, config)
    first = any(_first_person(account, config) for account in [text, *comment_texts])
    identity = any(_identity_groups(account, config) for account in [text, *comment_texts])
    action_result = any(
        _has(account, _terms(config, "action_terms"))
        and _has(account, _terms(config, "consequence_terms"))
        for account in [text, *comment_texts]
    )
    consequence = any(
        _has(account, _terms(config, "consequence_terms")) for account in [text, *comment_texts]
    )
    comments = any(v["is_first_person"] for v in discussion)
    raw_comments = []
    for key in ("comments", "replies"):
        values = item.metadata.get(key)
        if isinstance(values, list):
            raw_comments.extend(str(value) for value in values)
    comments = comments or any(_first_person(value, config) for value in raw_comments)
    comments = comments or any(_first_person(value, config) for value in comment_texts)
    viewpoints = len({v["stance"] for v in discussion if v["stance"]}) >= 2
    evidence = len(spans) >= 2 or item.verification_state == "verified"
    fresh = bool(item.published_at and now - timedelta(days=7) <= item.published_at <= now)
    flags = {
        "first_person": float(first),
        "specific_identity": float(identity),
        "action_result_structure": float(action_result),
        "consequence_terms": float(consequence),
        "discussion_engagement": float(
            item.engagement_metrics.get("comments", 0) > 0
            or bool(discussion)
            or bool(raw_comments)
            or bool(comment_texts)
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
    fallback, _ = fallback_story_score(item, config, now)
    richness = story_richness_score(item, config, now)
    evidence = list(
        dict.fromkeys(
            [item.title, *[s for s in (action, consequence, before, after, conflict) if s]]
        )
    )
    # A role match is a triage hint, not an observed actor; HN submitter != blog author.
    person = next((span for span in spans if _first_person(span, config)), "")
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
        copy.first_person_signal = [span for span in _spans(item) if _first_person(span, config)]
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
    for index, _candidate in enumerate(candidates):
        key = items[index].metadata.get("story_theme", "")
        if key:
            buckets[key].append(index)
    for key, indexes in buckets.items():
        if len(indexes) < 2:
            continue
        # Duplicate links/reposts do not establish independent cases. Only explicit
        # distinct actor evidence from completed mining can upgrade claim scope.
        independent = []
        seen = set()
        for index in indexes:
            actor = items[index].metadata.get("case_author")
            url = items[index].metadata.get("case_url")
            if actor and actor.casefold() not in seen and url not in seen:
                independent.append(index)
                seen.update((actor.casefold(), url))
        cluster_id = "cluster-" + hashlib.sha1(key.encode()).hexdigest()[:10]
        cases = [candidates[index].id for index in independent]
        for index in indexes:
            candidates[index].story_cluster_id = cluster_id
            if len(independent) >= 2:
                candidates[index].claim_scope = "multiple_cases"
                items[index].claim_scope = "multiple_cases"
            items[index].story_cluster_id = cluster_id
            items[index].story_cluster = {
                "story_cluster_id": cluster_id,
                "theme": key,
                "independent_cases": cases,
                "shared_pattern": key,
                "related_cases": [candidates[i].id for i in indexes],
                # A concern is not evidence that two cases contradict each other.
                "conflicting_cases": [],
            }


def fast_story_filter(
    items: list[ContentItem], config: dict, limit: int | None = None
) -> list[ContentItem]:
    limit = limit or config.get("fast_filter", {}).get("limit", 50)
    fast_config = config.get("fast_filter", {})
    threshold = fast_config.get("minimum_score", 40)
    ranked = sorted(
        items,
        key=lambda item: (-item.story_richness_score, -item.fallback_story_score, item.id),
    )
    eligible = [item for item in ranked if item.story_richness_score >= threshold]
    target = min(limit, fast_config.get("target_minimum", 30))
    if len(eligible) < target:
        selected_ids = {item.id for item in eligible}
        reserve = [item for item in ranked if item.id not in selected_ids]
        eligible.extend(reserve[: target - len(eligible)])
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


def story_spans(item):
    spans = evidence_spans(item)
    for index, comment in enumerate(item.metadata.get("discussion_comments", [])):
        if comment.get("evidence") and comment.get("url"):
            spans[f"c{index}"] = comment["evidence"]
    return spans


def story_request(item, config, model):
    spans = story_spans(item)
    post = {key: text for key, text in spans.items() if key.startswith("s")}
    accounts = [("post", post)] + [
        (key, {key: text}) for key, text in spans.items() if key.startswith("c")
    ]

    def account_strength(account):
        text = " ".join(account[1].values())
        return (
            20 * _first_person(text, config)
            + 15 * _has(text, _terms(config, "action_terms"))
            + 15 * _has(text, _terms(config, "consequence_terms"))
            + 10 * bool(_identity_groups(text, config))
            + min(len(text), 600) / 100
        )

    # Independent field questions cannot coordinate actor selection. Fix ONE
    # evidence account first, then let every field select only within it.
    primary_id, primary_spans = max(accounts, key=account_strength)
    questions = {
        field: {
            "type": "choice",
            "instructions": POLICY
            + description
            + " All story fields must describe ONE actual actor and action-result chain. "
            "Do not combine a post author's action with a commenter's outcome.",
            "criteria": {"NONE": "Not stated for this actor", **primary_spans},
        }
        for field, description in config["structure_fields"].items()
    }
    for key, instruction in {
        "personal_event": (
            "Does the evidence describe a real specific person's or small team's OWN lived "
            "experience with an action and a reported result? Company announcements, funding, "
            "future plans, generic users, feature promises, hypothetical benefits and pure "
            "technology specs are NO. First-person corporate 'we' is NOT a personal account."
        ),
        "realized_result": (
            "Does the same actual actor report what actually happened after their action? "
            "An implemented personal tool can be a result, but a plan, goal, ability claim, "
            "company deployment announcement or intended benefit alone is NO."
        ),
        "actual_conflict": (
            "Is there a concrete reported disagreement or tradeoff involving the actor? "
            "A routine action, word 'but', feature list or imagined conflict is NO."
        ),
        "actual_before_after": (
            "Does the actor's account explicitly supply BOTH a prior state and a changed "
            "later state? Generic 'now', launch dates or repeated sentences alone are NO."
        ),
    }.items():
        questions[key] = {
            "type": "noul",
            "instructions": POLICY + "Evaluate ONLY `primary_account` and its `primary_spans`; "
            "do not borrow another person's experience from discussion spans. " + instruction,
        }
    questions["theme"] = {
        "type": "choice",
        "instructions": POLICY + "Select the phenomenon evidenced by an actual personal account; "
        "do not classify company promises.",
        "criteria": {"NONE": "No supported phenomenon", **config.get("cluster_themes", {})},
    }
    # A stance is a label on a real bounded excerpt, never a made-up comment.
    for key in spans:
        if key.startswith("c"):
            questions[f"view_{key}"] = {
                "type": "choice",
                "instructions": POLICY
                + f"Classify the actually expressed viewpoint in span {key}. "
                "Other comments may supply context, but do not invent support/opposition.",
                "criteria": {
                    "NONE": "No clear view",
                    "benefit": "Reports benefit",
                    "concern": "Reports concern or disadvantage",
                    "mixed": "Explicit tradeoff",
                    "question": "Asks a real question",
                    "other": "Other stated viewpoint",
                },
            }
    return {
        "model": model,
        "state": {
            "item": {
                "title": item.title,
                "url": item.canonical_url,
                "author_note": "submitter is not necessarily original author",
                "verification": item.verification_state,
            },
            "spans": spans,
            "primary_account": primary_id,
            "primary_spans": primary_spans,
            "reader_identity_pool": config.get("reader_identities", []),
        },
        "questions": questions,
    }


class StoryJudge(SemanticJudge):
    def __init__(self, provider_config, story_config, store, http=None):
        super().__init__(provider_config, {}, store, http)
        self.story_config = story_config

    def prepare(self, item):
        request = story_request(item, self.story_config, self.config["provider"]["model"])
        digest = hashlib.sha256(
            json.dumps(request, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return request, f"story_judgment:{digest}"


def compose_story(item, response, config, mode="live", error=None):
    result = item.model_copy(deep=True)
    result.metadata["story_semantic"] = {"mode": mode, "error": error}
    result.claim_scope = "unassessed"
    if response is None:
        result.story_mining_status = "needs_review"
        result.metadata["story_semantic"]["note"] = "Local structure is a triage hypothesis only."
        return result
    spans = story_spans(item)
    minimum = config.get("evidence_probability", 0.65)
    fields, selected_ids = {}, {}
    for field in config["structure_fields"]:
        answer = response.answers[field]
        key = answer.choice
        if (
            key in spans
            and 1 - answer.probabilities.get("NONE", 1) >= minimum
            and answer.probabilities.get(key, 0) >= 0.35
        ):
            fields[field], selected_ids[field] = spans[key], key
        else:
            fields[field] = ""
    # All three core fields must come from the same firsthand account.
    origins = {
        ("post" if selected_ids.get(k, "").startswith("s") else selected_ids.get(k))
        for k in ("who", "did_what", "what_happened")
        if fields[k]
    }
    complete = (
        all(fields[k] for k in ("who", "did_what", "what_happened"))
        and len(origins) == 1
        and response.answers["personal_event"].noul >= minimum
        and response.answers["realized_result"].noul >= minimum
    )
    borderline = (
        len(origins) == 1
        and response.answers["personal_event"].noul >= 0.5
        and response.answers["realized_result"].noul >= 0.5
        and all(fields[k] for k in ("who", "did_what", "what_happened"))
    )
    if not complete:
        fields["what_happened"] = ""
    if response.answers["actual_conflict"].noul < minimum:
        fields["conflict"] = ""
    if (
        response.answers["actual_before_after"].noul < minimum
        or fields["before_state"] == fields["after_state"]
    ):
        fields["before_state"] = fields["after_state"] = ""
    core_origin = next(iter(origins), None) if len(origins) == 1 else None
    for field, selected in selected_ids.items():
        origin = "post" if selected.startswith("s") else selected
        if field not in {"who", "did_what", "what_happened"} and origin != core_origin:
            fields[field] = ""
    result.story_structure = fields
    result.story_conflict = fields["conflict"]
    result.claim_scope = "single_case" if complete else "unassessed"
    viewpoints = []
    for index, comment in enumerate(item.metadata.get("discussion_comments", [])):
        answer = response.answers.get(f"view_c{index}")
        if answer and answer.choice != "NONE" and answer.probabilities.get(answer.choice, 0) >= 0.5:
            viewpoints.append(
                {
                    **comment,
                    "stance": answer.choice,
                    "is_first_person": _first_person(comment["evidence"], config),
                }
            )
    result.discussion_viewpoints = viewpoints
    dimensions = {
        "first_person": float(
            any(_first_person(value, config) for value in fields.values() if value)
        ),
        "concrete_actor": float(bool(fields["who"])),
        "specific_action": float(bool(fields["did_what"])),
        "consequence": float(bool(fields["what_happened"])),
        "before_after": float(
            bool(
                fields["before_state"]
                and fields["after_state"]
                and fields["before_state"] != fields["after_state"]
            )
        ),
        "conflict": float(bool(fields["conflict"])),
        "numbers": float(_number_signal(" ".join(fields.values()))),
        "first_person_comments": float(any(v["is_first_person"] for v in viewpoints)),
        "multiple_viewpoints": float(len({v["stance"] for v in viewpoints}) > 1),
        "evidence_quality": float(len(set(v for v in fields.values() if v)) > 1),
    }
    result.story_richness_score = round(
        sum(dimensions[k] * w for k, w in config["weights"].items()), 2
    )
    if not complete:
        result.story_richness_score = min(result.story_richness_score, 39)
    result.story_mining_status = (
        "candidate"
        if complete and result.story_richness_score >= 40
        else "needs_review"
        if borderline
        else "weak"
    )
    theme = response.answers["theme"]
    if complete and theme.choice != "NONE" and theme.probabilities.get(theme.choice, 0) >= 0.5:
        result.metadata["story_theme"] = theme.choice
    result.metadata["story_semantic"].update(
        fields=selected_ids,
        dimensions=dimensions,
        gates={
            key: response.answers[key].noul
            for key in (
                "personal_event",
                "realized_result",
                "actual_conflict",
                "actual_before_after",
            )
        },
    )
    actor_id = selected_ids.get("who", "")
    if actor_id.startswith("c"):
        comment = item.metadata["discussion_comments"][int(actor_id[1:])]
        result.metadata["case_author"] = comment.get("author")
        result.metadata["case_url"] = comment.get("url")
    elif (
        item.source_type in {"manual", "personal_blog", "developer_blog", "creator_post"}
        or item.metadata.get("evidence_role") == "personal_author_account"
    ):
        result.metadata["case_author"] = item.author
        result.metadata["case_url"] = item.canonical_url
    elif item.canonical_url == item.metadata.get("discussion_url"):
        # A self-post has its own author; a submitted external link does not.
        result.metadata["case_author"] = item.author
        result.metadata["case_url"] = item.canonical_url
    return result


def candidate_from_item(item):
    fields = item.story_structure
    semantic = item.metadata.get("story_semantic", {})
    return StoryCandidate(
        id=f"story-{item.id}",
        source_item_ids=[item.id],
        primary_person=fields.get("who", ""),
        action=fields.get("did_what", ""),
        result=fields.get("what_happened", ""),
        context=item.title,
        identity_group=[fields["identity"]] if fields.get("identity") else [],
        before_state=fields.get("before_state", ""),
        after_state=fields.get("after_state", ""),
        change_event=fields.get("what_changed", ""),
        conflict=item.story_conflict,
        surprise=fields.get("unexpected_part", ""),
        money_signal=fields.get("what_it_cost", ""),
        emotion_signal=fields.get("emotion", ""),
        evidence_spans=list(dict.fromkeys([item.title, *[v for v in fields.values() if v]])),
        discussion_evidence=item.discussion_viewpoints,
        engagement=item.engagement_metrics,
        claim_scope=item.claim_scope,
        verification_state=item.verification_state,
        story_strength=item.story_richness_score,
        story_value=item.story_richness_score,
        fallback_story_score=item.fallback_story_score,
        source_tier=item.metadata.get("story_mining", {}).get("tier", "C"),
        source_authority=item.source_reliability,
        evidence_gaps=[
            f"Missing: {key}"
            for key in (
                "who",
                "did_what",
                "what_happened",
                "before_state",
                "after_state",
                "identity",
            )
            if not fields.get(key)
        ]
        + (
            ["Firsthand account is not independently verified"]
            if item.verification_state != "verified"
            else []
        ),
        human_trigger_score=item.human_trigger_score,
        viral_potential=item.viral_potential,
        story_type=(
            "needs_review"
            if semantic.get("mode") == "unavailable"
            else "before_after"
            if fields.get("before_state") and fields.get("after_state")
            else "single_case"
        ),
    )


def discover_stories(items, discovery_config, config, priority, now):
    # Exact URL deduplication preserves separately authored cases with similar titles.
    by_url = {}
    for item in items:
        if item.published_at is None:
            if item.source_type != "manual":
                continue
        elif not (
            0
            <= (now - item.published_at).total_seconds()
            <= discovery_config["max_age_days"] * 86400
        ):
            continue
        existing = by_url.get(item.canonical_url)
        if existing is None or len(item.metadata.get("discussion_comments", [])) > len(
            existing.metadata.get("discussion_comments", [])
        ):
            by_url[item.canonical_url] = item
    enriched, _ = enrich_story_items(list(by_url.values()), config, priority, now)
    # No source authority or discovery-score gate precedes story mining.
    return enriched
