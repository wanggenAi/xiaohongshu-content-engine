"""Active public searches are independent of Story Mining and ordinary feed collection."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import feedparser

from .collectors import client, collect_rss, raw_item
from .normalize import clean_excerpt
from .telegram_public import collect_public


def scan(config, people, telegram, inbox=(), http=None):
    owned = http is None
    http = http or client()
    now = datetime.now(UTC)
    queries = [(q, "hot_topic") for q in config["queries"]]
    queries += [
        (p["name"] + " AI interview announcement", "celebrity_watch") for p in people["people"]
    ]

    def news_search(task):
        query, kind = task
        tried, rows = [], []
        for hours in config["windows_hours"]:
            period = {24: "1d", 72: "3d", 168: "7d"}[hours]
            response = http.get(
                config["news_search_url"],
                params={"q": f"{query} when:{period}", "hl": "en-US", "gl": "US", "ceid": "US:en"},
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:8]:
                parsed = entry.get("published_parsed")
                published = datetime(*parsed[:6], tzinfo=UTC) if parsed else None
                if not published or not now - timedelta(hours=hours) <= published <= now:
                    continue
                row = raw_item(
                    {"name": "live_news_search", "type": "hot_search", "reliability": 0.4},
                    entry.link,
                    entry.title,
                    published_at=published,
                    raw_excerpt=clean_excerpt(entry.get("summary", "")),
                )
                row["metadata"].update(
                    search_query=query,
                    search_window_hours=hours,
                    discovery_channel=kind,
                    evidence_status="search_only",
                    evidence_scope="search result; publisher text not verified",
                    scan_observed_at=now.isoformat(),
                )
                rows.append(row)
            tried.append({"window_hours": hours, "hits": len(rows)})
            if rows:
                break
        return rows, {
            "query": query,
            "channel": kind,
            "status": "ok" if rows else "empty",
            "windows": tried,
        }

    def discussion_search(query):
        response = http.get(
            config["public_discussion_api"],
            params={
                "query": query,
                "tags": "story",
                "numericFilters": f"created_at_i>{int((now - timedelta(days=7)).timestamp())}",
                "hitsPerPage": 8,
            },
        )
        response.raise_for_status()
        rows = []
        for hit in response.json().get("hits", []):
            url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
            row = raw_item(
                {"name": "live_discussion_search", "type": "hot_discussion", "reliability": 0.5},
                hit.get("url") or url,
                hit["title"],
                author=hit.get("author"),
                published_at=hit["created_at"],
                raw_excerpt=clean_excerpt(hit.get("story_text") or ""),
                engagement_metrics={
                    "points": hit.get("points") or 0,
                    "comments": hit.get("num_comments") or 0,
                },
            )
            row["metadata"].update(
                discussion_url=url,
                original_platform="hacker_news",
                search_query=query,
                evidence_scope=(
                    "public submission and observed engagement; headline is not full article"
                ),
                evidence_status="discussion_headline",
                engagement_observed_at=now.isoformat(),
                scan_observed_at=now.isoformat(),
            )
            rows.append(row)
        return rows, {
            "query": query,
            "channel": "viral_discussion",
            "status": "ok" if rows else "empty",
            "hits": len(rows),
        }

    def safe(function, arg):
        try:
            return function(arg)
        except Exception as exc:
            return [], {
                "query": arg[0] if isinstance(arg, tuple) else arg,
                "status": "error",
                "reason": type(exc).__name__,
            }

    rows, audit = [], []
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(safe, news_search, q) for q in queries]
            futures += [
                pool.submit(safe, discussion_search, q)
                for q in config.get("discussion_queries", config["queries"])
            ]
            futures += [
                pool.submit(
                    safe,
                    lambda source: (
                        collect_rss(source, http)[0],
                        {"channel": "official_rss", "source": source["name"], "status": "ok"},
                    ),
                    source,
                )
                for source in config.get("official_sources", [])
            ]
            for future in futures:
                found, details = future.result()
                for row in found:
                    row["metadata"]["scan_observed_at"] = now.isoformat()
                rows.extend(found)
                audit.append(details)
        found, telegram_audit = collect_public(telegram, http, inbox)
        for row in found:
            row["metadata"]["scan_observed_at"] = now.isoformat()
        rows.extend(found)
        audit.extend({"channel": "telegram_public", **a} for a in telegram_audit)
    finally:
        if owned:
            http.close()
    return rows, {
        "scanned_at": now.isoformat(),
        "windows_hours": config["windows_hours"],
        "queries": audit,
        "telegram": telegram_audit,
        "raw_items": len(rows),
        "people_monitored": [p["name"] for p in people["people"]],
    }
