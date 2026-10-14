import json
import sqlite3
from pathlib import Path

from .models import ContentItem, ContentPerformance, EditorialFeedback
from .normalize import canonicalize


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS inbox (url TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS content_performance
                (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS editorial_assessments
                (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS editorial_feedback
                (sequence INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL,
                 body TEXT NOT NULL);
        """)

    def save_batch(self, items: list[ContentItem], state: dict | None = None):
        # Persist items and the Telegram offset together BEFORE the next getUpdates call.
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO items VALUES (?, ?)",
                [(item.id, item.model_dump_json()) for item in items],
            )
            for key, value in (state or {}).items():
                self.db.execute(
                    "INSERT OR REPLACE INTO state VALUES (?, ?)", (key, json.dumps(value))
                )

    def items(self) -> list[ContentItem]:
        return [
            ContentItem.model_validate_json(row[0])
            for row in self.db.execute("SELECT body FROM items ORDER BY id")
        ]

    def get_state(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def add_inbox(self, url: str, **details):
        url = canonicalize(url)
        # URL-only input cannot replace evidence already supplied by the user.
        old = self.db.execute("SELECT body FROM inbox WHERE url = ?", (url,)).fetchone()
        body = json.loads(old[0]) if old else {}
        body.update({k: v for k, v in details.items() if v is not None})
        body["url"] = url
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO inbox VALUES (?, ?)",
                (url, json.dumps(body, ensure_ascii=False)),
            )
        return url

    def inbox(self):
        return [json.loads(row[0]) for row in self.db.execute("SELECT body FROM inbox")]

    def save_performance(self, record: ContentPerformance):
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO content_performance VALUES (?, ?)",
                (record.id, record.model_dump_json()),
            )

    def prune(self, cutoff: str):
        # Manual references remain until the user removes the data directory.
        with self.db:
            self.db.execute(
                """DELETE FROM items WHERE
                json_extract(body, '$.source_type') != 'manual' AND
                json_extract(body, '$.fetched_at') < ?""",
                (cutoff,),
            )

            self.db.execute(
                """DELETE FROM state WHERE (key LIKE 'editorial_judgment:%'
                OR key LIKE 'human_judgment:%' OR key LIKE 'story_judgment:%')
                AND (json_extract(value, '$.evaluated_at') < ?
                OR json_extract(value, '$.evaluated_at') IS NULL)""",
                (cutoff,),
            )

            self.db.execute(
                """DELETE FROM editorial_assessments WHERE
                json_extract(body, '$.fetched_at') < ?""",
                (cutoff,),
            )

    def save_assessments(self, items):
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO editorial_assessments VALUES (?, ?)",
                [(item.id, item.model_dump_json()) for item in items],
            )

    def save_editorial_feedback(self, record: EditorialFeedback):
        with self.db:
            self.db.execute(
                "INSERT INTO editorial_feedback(candidate_id, body) VALUES (?, ?)",
                (record.candidate_id, record.model_dump_json()),
            )

    def editorial_feedback(self, candidate_id=None):
        query = "SELECT body FROM editorial_feedback"
        args = ()
        if candidate_id:
            query += " WHERE candidate_id = ?"
            args = (candidate_id,)
        query += " ORDER BY sequence"
        return [
            EditorialFeedback.model_validate_json(row[0]) for row in self.db.execute(query, args)
        ]
