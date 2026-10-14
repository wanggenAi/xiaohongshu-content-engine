"""Append a confirmed public post without duplicating an existing receipt."""

import json
from pathlib import Path

from .models import PublishedPost


def record_publication(path: Path, record: PublishedPost) -> bool:
    existing = (
        [json.loads(line) for line in path.read_text().splitlines() if line]
        if path.exists()
        else []
    )
    for row in existing:
        if row["post_url"] == record.post_url:
            if row != record.model_dump(mode="json"):
                raise ValueError("post URL already recorded with different publication data")
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(record.model_dump_json() + "\n")
    return True
