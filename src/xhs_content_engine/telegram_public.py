"""No-login public Telegram pages; no bot credential, private groups or invite URLs."""

import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .collectors import raw_item
from .normalize import clean_excerpt


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return " ".join(c.text() if isinstance(c, Node) else c for c in self.children)

    def find(self, class_name):
        found = [self] if class_name in self.attrs.get("class", "").split() else []
        for child in self.children:
            if isinstance(child, Node):
                found.extend(child.find(class_name))
        return found


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"br", "img", "meta", "link", "input", "hr", "source", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def public_url(value):
    parts = urlsplit(value if "://" in value else f"https://t.me/{value}")
    if parts.scheme != "https" or parts.hostname != "t.me" or parts.username or parts.port:
        raise ValueError("only public https://t.me channel or post URLs allowed")
    path = parts.path.removeprefix("/s/").strip("/")
    bits = path.split("/")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", bits[0]) or bits[0].lower() in {
        "joinchat",
        "share",
        "proxy",
        "login",
        "c",
        "addstickers",
        "iv",
    }:
        raise ValueError("private, invitation or service URL forbidden")
    if len(bits) > 2 or len(bits) == 2 and not bits[1].isdigit():
        raise ValueError("expected channel username or numeric public post ID")
    return f"https://t.me/s/{path}"


def parse_public(html, expected_channel):
    page = Page()
    page.feed(html)
    rows = []
    for message in page.root.find("tgme_widget_message"):
        post = message.attrs.get("data-post", "")
        if not re.fullmatch(re.escape(expected_channel) + r"/\d+", post, re.I):
            continue
        texts = message.find("tgme_widget_message_text")
        dates = message.find("tgme_widget_message_date")
        times = []
        for date in dates:
            times.extend(c for c in date.children if isinstance(c, Node) and c.tag == "time")
        text = clean_excerpt(texts[0].text()) if texts else ""
        if not text or not times:
            continue  # Media-only cannot become a made-up visual description.
        published = datetime.fromisoformat(times[0].attrs["datetime"].replace("Z", "+00:00"))
        if published.tzinfo is None:
            continue
        views = message.find("tgme_widget_message_views")
        metrics = {}
        if views:
            match = re.fullmatch(r"([\d.]+)([KM]?)", views[0].text().strip(), re.I)
            if match:
                metrics["views"] = int(
                    float(match[1]) * {"": 1, "K": 1000, "M": 1000000}[match[2].upper()]
                )
        row = raw_item(
            {"name": "telegram_public", "type": "telegram_public", "reliability": 0.4},
            f"https://t.me/{post}",
            text[:180],
            author=expected_channel,
            published_at=published,
            raw_excerpt=text,
            engagement_metrics=metrics,
        )
        row["metadata"].update(
            original_platform="telegram",
            evidence_scope="public post text and displayed views; claims need corroboration",
            evidence_status="public_post_unverified_claims",
            engagement_observed_at=datetime.now().astimezone().isoformat(),
        )
        rows.append(row)
    return rows


def collect_public(config, http, inbox=()):
    targets = [c["public_url"] for c in config.get("channels", [])]
    targets += config.get("post_urls", [])
    targets += [e["url"] for e in inbox if urlsplit(e["url"]).hostname in {"t.me", "telegram.me"}]
    rows, audit = [], []
    for target in dict.fromkeys(targets):
        try:
            url = public_url(target)
            response = http.get(url, follow_redirects=False)
            response.raise_for_status()
            channel = urlsplit(url).path.split("/")[2]
            posts = parse_public(response.text, channel)
            bits = urlsplit(url).path.strip("/").split("/")
            if len(bits) == 3:
                posts = [p for p in posts if p["canonical_url"].endswith("/" + bits[2])]
            rows.extend(posts[-config.get("max_posts_per_channel", 20) :])
            audit.append(
                {
                    "url": url,
                    "status": "ok" if posts else "empty_or_login_required",
                    "posts": len(posts),
                }
            )
        except Exception as exc:
            audit.append({"url": target, "status": "error", "reason": type(exc).__name__})
    return rows, audit
