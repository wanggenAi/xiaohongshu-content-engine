from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from xhs_content_engine.models import ContentPerformance, PublishedPost
from xhs_content_engine.publication import record_publication


def test_confirmed_receipt_is_idempotent_and_rejects_conflicts(tmp_path):
    record = PublishedPost(
        candidate_id="actual-candidate",
        published_at=datetime(2026, 10, 14, tzinfo=UTC),
        post_url="https://www.xiaohongshu.com/explore/test-post",
        title="Example",
        content_type="TECH_SHIFT",
        platform_status="发布成功",
        publication_evidence="local confirmation screenshot",
    )
    path = tmp_path / "published_posts.jsonl"
    assert record_publication(path, record)
    assert not record_publication(path, record)
    assert len(path.read_text().splitlines()) == 1
    with pytest.raises(ValueError, match="different publication data"):
        record_publication(path, record.model_copy(update={"title": "Changed"}))
    for updates in [
        {"initial_status": "draft"},
        {"post_url": "https://creator.xiaohongshu.com/publish/publish"},
        {"published_at": datetime(2026, 10, 14)},
    ]:
        with pytest.raises(ValidationError):
            PublishedPost.model_validate(record.model_dump() | updates)


def test_missing_performance_is_unknown_and_observed_zero_is_valid():
    record = ContentPerformance(
        id="example",
        published_at=datetime.now(UTC),
        topic="Traffic",
        content_type="TECH_SHIFT",
        title="Example",
        internal_source="author_blog",
        public_source_label="海外开发者",
        metrics_2h={"impressions": 20, "likes": 0},
    )
    assert record.views is None
    assert record.likes is None
    assert record.metrics_2h["likes"] == 0
