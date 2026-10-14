from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, computed_field, field_validator


class ContentType(StrEnum):
    AI_PRODUCT = "AI_PRODUCT"
    HUMAN_AI_STORY = "HUMAN_AI_STORY"
    DEVELOPER_STORY = "DEVELOPER_STORY"
    BIG_PERSON_IDEA = "BIG_PERSON_IDEA"
    OVERSEAS_DISCUSSION = "OVERSEAS_DISCUSSION"
    TECH_SHIFT = "TECH_SHIFT"
    CAREER_SHIFT = "CAREER_SHIFT"
    BUSINESS_SIGNAL = "BUSINESS_SIGNAL"
    INTERESTING_INTERNET = "INTERESTING_INTERNET"


class ContentItem(BaseModel):
    id: str
    source: str
    source_type: str
    canonical_url: str
    title: str = Field(min_length=1, max_length=500)
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    language: str = "unknown"
    raw_excerpt: str = Field(default="", max_length=600)
    summary: str = Field(default="", max_length=600)
    engagement_metrics: dict[str, int] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    content_type: ContentType = ContentType.INTERESTING_INTERNET
    source_reliability: float = Field(default=0.5, ge=0, le=1)
    duplicate_group: str | None = None
    score: float = Field(default=0, ge=0, le=100)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    verification_state: str = "needs_review"
    rights_note: str = "仅保留必要摘录；图片、视频、全文未获得转载授权。"
    public_source_label: str = "海外"
    metadata: dict[str, Any] = Field(default_factory=dict)

    editorial_score: float = Field(default=0, ge=0, le=100)
    editorial_value: dict[str, Any] = Field(default_factory=dict)
    editorial_score_breakdown: dict[str, Any] = Field(default_factory=dict)
    editorial_reject_reason: list[str] = Field(default_factory=list)
    editorial_verdict: str = "WEAK"
    editorial_title_seed: str = ""
    story_signals: dict[str, list[str]] = Field(default_factory=dict)
    editorial_questions: list[str] = Field(default_factory=list)
    core_story: str = ""
    why_this_may_work: str = ""
    why_this_may_fail: str = ""
    missing_evidence: list[str] = Field(default_factory=list)
    possible_angles: list[str] = Field(default_factory=list)
    semantic_status: str = "unavailable"
    human_trigger_score: float | None = Field(default=None, ge=0, le=100)
    human_trigger_map: dict[str, Any] = Field(default_factory=dict)
    human_trigger_breakdown: dict[str, Any] = Field(default_factory=dict)
    viral_potential: float | None = Field(default=None, ge=0, le=100)
    strongest_triggers: list[str] = Field(default_factory=list, max_length=2)
    human_trigger_summary: str = ""
    scene: dict[str, str] = Field(default_factory=dict)
    reader_self_projection: str = ""
    emotional_tension: str = ""
    reversal: dict[str, str] = Field(default_factory=dict)
    likely_comment_routes: list[str] = Field(default_factory=list)
    human_title_seed: str = ""
    human_title_seeds: list[dict[str, str]] = Field(default_factory=list)
    claim_scope: str = "unassessed"
    story_patterns: list[str] = Field(default_factory=list)
    human_review_reason: str = ""
    # Story Mining is deliberately separate from semantic editorial scores. These
    # fields contain extracted evidence and deterministic triage signals only.
    story_richness_score: float = Field(default=0, ge=0, le=100)
    fallback_story_score: float = Field(default=0, ge=0, le=100)
    story_structure: dict[str, str] = Field(default_factory=dict)
    story_conflict: str = ""
    discussion_viewpoints: list[dict[str, Any]] = Field(default_factory=list)
    story_cluster_id: str = ""
    story_cluster: dict[str, Any] = Field(default_factory=dict)
    story_mining_status: str = "unassessed"
    first_person_signal: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def discovery_score(self) -> float:
        return self.score

    @computed_field
    @property
    def total_score(self) -> float:
        return self.score

    @field_validator("canonical_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        from .normalize import canonicalize

        return canonicalize(value)

    @field_validator("published_at", "fetched_at")
    @classmethod
    def aware_dates(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must include a timezone")
        return value

    @field_validator("engagement_metrics")
    @classmethod
    def nonnegative_metrics(cls, value: dict[str, int]) -> dict[str, int]:
        if any(number < 0 for number in value.values()):
            raise ValueError("engagement metrics must be nonnegative")
        return value


class ContentPerformance(BaseModel):
    id: str
    published_at: datetime
    topic: str
    content_type: ContentType
    title: str
    internal_source: str
    public_source_label: str
    # Missing measurements are unknown, never fabricated zeroes.
    views: int | None = Field(default=None, ge=0)
    impressions: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    follows: int | None = Field(default=None, ge=0)
    observed_at: datetime | None = None
    measurement_source: str | None = None
    snapshot_observed_at: dict[str, datetime] = Field(default_factory=dict)
    metrics_2h: dict[str, int] = Field(default_factory=dict)
    metrics_24h: dict[str, int] = Field(default_factory=dict)
    metrics_72h: dict[str, int] = Field(default_factory=dict)

    @field_validator("metrics_2h", "metrics_24h", "metrics_72h")
    @classmethod
    def validate_snapshots(cls, value: dict[str, int]) -> dict[str, int]:
        allowed = {"impressions", "views", "likes", "saves", "comments", "shares", "follows"}
        if set(value) - allowed or any(v < 0 for v in value.values()):
            raise ValueError("invalid performance metrics")
        return value


class PublishedPost(BaseModel):
    """Only confirmed submissions belong in the publication ledger."""

    candidate_id: str = Field(min_length=1)
    published_at: datetime
    platform: str = "xiaohongshu"
    published_time_precision: Literal["minute", "second"] = "second"
    post_url: str
    title: str = Field(min_length=1)
    content_type: ContentType
    story_richness_score: float | None = Field(default=None, ge=0, le=100)
    human_trigger_score: float | None = Field(default=None, ge=0, le=100)
    viral_potential: float | None = Field(default=None, ge=0, le=100)
    initial_status: str = "published"
    platform_status: str = Field(min_length=1)
    publication_evidence: str = Field(min_length=1)

    @field_validator("published_at")
    @classmethod
    def publication_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("published_at must include a timezone")
        return value

    @field_validator("post_url")
    @classmethod
    def public_post_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname
            not in {"www.xiaohongshu.com", "xiaohongshu.com", "xhslink.com", "www.xhslink.com"}
            or parsed.path in {"", "/"}
        ):
            raise ValueError("a real Xiaohongshu post URL is required")
        return value

    @field_validator("platform", "initial_status")
    @classmethod
    def confirmed_publication(cls, value: str, info) -> str:
        expected = "xiaohongshu" if info.field_name == "platform" else "published"
        if value != expected:
            raise ValueError(f"{info.field_name} must be {expected}")
        return value


class StoryCandidate(BaseModel):
    """Evidence-backed person/event record produced before Human Trigger scoring."""

    id: str
    source_item_ids: list[str] = Field(min_length=1)
    story_type: str = "single_case"
    primary_person: str = ""
    identity_group: list[str] = Field(default_factory=list)
    action: str = ""
    context: str = ""
    before_state: str = ""
    change_event: str = ""
    after_state: str = ""
    result: str = ""
    conflict: str = ""
    surprise: str = ""
    money_signal: str = ""
    job_signal: str = ""
    emotion_signal: str = ""
    evidence_spans: list[str] = Field(min_length=1)
    discussion_evidence: list[dict[str, Any]] = Field(default_factory=list)
    engagement: dict[str, int] = Field(default_factory=dict)
    claim_scope: str = "single_case"
    verification_state: str = "needs_review"
    story_strength: float = Field(default=0, ge=0, le=100)
    fallback_story_score: float = Field(default=0, ge=0, le=100)
    story_cluster_id: str = ""
    source_tier: str = "C"
    source_authority: float = Field(default=0.5, ge=0, le=1)
    story_value: float = Field(default=0, ge=0, le=100)
    evidence_gaps: list[str] = Field(default_factory=list)
    human_trigger_score: float | None = Field(default=None, ge=0, le=100)
    viral_potential: float | None = Field(default=None, ge=0, le=100)

    @computed_field
    @property
    def story_richness_score(self) -> float:
        return self.story_strength


class EditorialFeedback(BaseModel):
    candidate_id: str = Field(min_length=1)
    decision: str
    user_quote: str = ""
    title: str = ""
    reasons: list[str] = Field(min_length=1)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value):
        if value not in {"LIKE", "MAYBE", "DISLIKE"}:
            raise ValueError("decision must be LIKE, MAYBE or DISLIKE")
        return value

    @field_validator("reasons")
    @classmethod
    def valid_reasons(cls, value):
        if any(not reason.strip() or len(reason) > 500 for reason in value):
            raise ValueError("reasons must be nonempty and at most 500 characters")
        return value
