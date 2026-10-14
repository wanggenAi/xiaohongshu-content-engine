from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

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
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    follows: int = Field(default=0, ge=0)
    metrics_2h: dict[str, int] = Field(default_factory=dict)
    metrics_24h: dict[str, int] = Field(default_factory=dict)
    metrics_72h: dict[str, int] = Field(default_factory=dict)

    @field_validator("metrics_2h", "metrics_24h", "metrics_72h")
    @classmethod
    def validate_snapshots(cls, value: dict[str, int]) -> dict[str, int]:
        allowed = {"views", "likes", "saves", "comments", "shares", "follows"}
        if set(value) - allowed or any(v < 0 for v in value.values()):
            raise ValueError("invalid performance metrics")
        return value
