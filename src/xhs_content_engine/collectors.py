"""Only official public APIs and publisher feeds; no login bypass or article scraping."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import feedparser
import httpx

from .normalize import clean_excerpt

USER_AGENT = (
    "xiaohongshu-content-engine/0.1 (+https://github.com/wanggenAi/xiaohongshu-content-engine)"
)


class SkipSource(Exception):
    pass


def client():
    return httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def json_get(http, url, **kwargs):
    response = http.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


def raw_item(config, url, title, **fields):
    return dict(
        source=config["name"],
        source_type=config["type"],
        canonical_url=url,
        title=title,
        source_reliability=config.get("reliability", 0.5),
        metadata={"original_url": url},
        **fields,
    )


def collect_hn(config, http):
    base = "https://hacker-news.firebaseio.com/v0"
    ids = json_get(http, f"{base}/topstories.json")[: config.get("limit", 60)]
    items, errors = [], 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [
            pool.submit(json_get, http, f"{base}/item/{identifier}.json") for identifier in ids
        ]
        for future in as_completed(futures):
            try:
                post = future.result()
                if not post or post.get("deleted") or post.get("dead"):
                    continue
                original = f"https://news.ycombinator.com/item?id={post['id']}"
                item = raw_item(
                    config,
                    post.get("url") or original,
                    post["title"],
                    author=post.get("by"),
                    language="en",
                    published_at=datetime.fromtimestamp(post["time"], UTC),
                    raw_excerpt=clean_excerpt(post.get("text", "")),
                    engagement_metrics={
                        "points": post.get("score", 0),
                        "comments": post.get("descendants", 0),
                    },
                )
                item["metadata"].update(
                    original_url=original,
                    discussion_url=original,
                    evidence_scope="headline and public discussion metrics",
                )
                items.append(item)
            except Exception:
                errors += 1
    if errors and not items:
        raise RuntimeError("all item requests failed")
    return items, {"item_errors": errors}


def github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def collect_github_search(config, http):
    cutoff = (datetime.now(UTC) - timedelta(days=30)).date()
    query = f"{config.get('query', 'topic:artificial-intelligence')} created:>={cutoff}"
    data = json_get(
        http,
        "https://api.github.com/search/repositories",
        headers=github_headers(),
        params={"q": query, "sort": "stars", "per_page": config.get("limit", 30)},
    )
    items = []
    for repo in data.get("items", []):
        item = raw_item(
            config,
            repo["html_url"],
            repo["full_name"],
            author=repo["owner"]["login"],
            published_at=repo["created_at"],
            raw_excerpt=repo.get("description") or "",
            tags=repo.get("topics", []),
            engagement_metrics={"stars": repo["stargazers_count"], "forks": repo["forks_count"]},
        )
        item["metadata"].update(
            evidence_scope="repository description and current star count",
            updated_at=repo["updated_at"],
            momentum_note="单次 stars 快照不能证明增长速度。",
        )
        items.append(item)
    return items, {}


def collect_github_releases(config, http):
    items, errors, last_error = [], 0, None
    for repo in config.get("repositories", []):
        try:
            releases = json_get(
                http,
                f"https://api.github.com/repos/{repo}/releases",
                headers=github_headers(),
                params={"per_page": config.get("limit", 3)},
            )
            for release in releases:
                if release.get("draft"):
                    continue
                item = raw_item(
                    config,
                    release["html_url"],
                    f"{repo}: {release.get('name') or release['tag_name']}",
                    author=release["author"]["login"],
                    published_at=release.get("published_at"),
                    raw_excerpt=clean_excerpt(release.get("body") or ""),
                )
                item["metadata"].update(
                    evidence_scope="release notes excerpt", flags=["minor_parameter_update"]
                )
                items.append(item)
        except Exception as exc:
            errors += 1
            last_error = exc
    if errors and not items:
        raise last_error
    return items, {"item_errors": errors}


def collect_rss(config, http):
    response = http.get(config["url"])
    response.raise_for_status()
    # Do not persist feed bytes/full articles. Only bounded editorial excerpts are retained.
    feed = feedparser.parse(response.content)
    if not feed.entries and feed.bozo:
        raise ValueError("invalid RSS/Atom response")
    items, errors = [], 0
    for entry in feed.entries[: config.get("limit", 20)]:
        if not entry.get("link") or not entry.get("title"):
            errors += 1
            continue
        parsed = entry.get("published_parsed")  # updated != original published timestamp
        published = datetime(*parsed[:6], tzinfo=UTC) if parsed else None
        item = raw_item(
            config,
            entry.link,
            entry.title,
            author=entry.get("author"),
            published_at=published,
            raw_excerpt=clean_excerpt(entry.get("summary", "")),
            language=feed.feed.get("language", "unknown"),
            tags=[tag.term for tag in entry.get("tags", []) if tag.get("term")][:10],
        )
        item["metadata"].update(feed_url=config["url"], evidence_scope="publisher RSS excerpt")
        items.append(item)
    return items, {"item_errors": errors}


def collect_manual(entries):
    items = []
    for entry in entries:
        host = urlsplit(entry["url"]).hostname
        platform = "telegram" if host == "t.me" else "manual"
        item = raw_item(
            {"name": platform, "type": "manual", "reliability": 0.3},
            entry["url"],
            entry.get("title") or f"Manual reference: {entry['url']}",
            author=entry.get("author"),
            published_at=entry.get("published_at"),
            raw_excerpt=entry.get("note") or "",
        )
        item["metadata"].update(
            original_platform=platform,
            flags=["unverified"] if entry.get("title") else ["unverified", "unclear_source"],
            evidence_scope="user supplied; URL not fetched",
        )
        items.append(item)
    return items


def telegram_batch(config, http, offset: int):
    token = os.getenv(config.get("token_env", "TELEGRAM_BOT_TOKEN"))
    if not token:
        raise SkipSource("missing TELEGRAM_BOT_TOKEN")
    channels = {str(c).lstrip("@").casefold() for c in config.get("channels", [])}
    if not channels:
        raise SkipSource("no authorized public channels configured")
    response = json_get(
        http,
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={
            "offset": offset,
            "limit": 100,
            "timeout": 1,
            "allowed_updates": '["channel_post","edited_channel_post"]',
        },
    )
    if not response.get("ok"):
        # Never include API URLs or exception strings; they contain the token.
        raise RuntimeError("Telegram API returned ok=false")
    updates = response.get("result", [])
    items, rejected = [], 0
    next_offset = offset
    for update in updates:
        next_offset = max(next_offset, int(update["update_id"]) + 1)
        post = update.get("channel_post") or update.get("edited_channel_post")
        if not post:
            continue
        chat = post.get("chat", {})
        username = chat.get("username", "")
        text = post.get("text") or post.get("caption") or ""
        if (
            chat.get("type") != "channel"
            or username.casefold() not in channels
            or not text
            or post.get("has_protected_content")
        ):
            rejected += 1
            continue
        url = f"https://t.me/{username}/{post['message_id']}"
        item = raw_item(
            config,
            url,
            clean_excerpt(text.splitlines()[0], 200),
            author=post.get("author_signature") or chat.get("title") or username,
            published_at=datetime.fromtimestamp(post["date"], UTC),
            raw_excerpt=clean_excerpt(text),
            public_source_label="海外社区",
        )
        # No invented views, likes, subscribers or forwarding statistics.
        item["metadata"].update(
            channel_username=username,
            message_id=post["message_id"],
            edited_at=post.get("edit_date"),
            original_platform="telegram",
            evidence_scope="authorized public channel message excerpt",
            forwarded=bool(post.get("forward_origin")),
            flags=["unverified"],
        )
        items.append(item)
    return items, next_offset, len(updates), rejected


ADAPTERS = {
    "hacker_news": collect_hn,
    "github_search": collect_github_search,
    "github_releases": collect_github_releases,
    "rss": collect_rss,
}
