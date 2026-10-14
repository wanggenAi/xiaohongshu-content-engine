import hashlib
import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING = {
    "fbclid",
    "gclid",
    "ref",
    "ref_src",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


def canonicalize(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("only absolute HTTP(S) URLs are accepted")
    if parts.username or parts.password:
        raise ValueError("URL credentials are forbidden")
    host = parts.hostname.lower()
    port = parts.port
    host = "t.me" if host in {"telegram.me", "www.telegram.me", "www.t.me"} else host
    netloc = f"[{host}]" if ":" in host else host
    if port and not (
        port == 443 and parts.scheme == "https" or port == 80 and parts.scheme == "http"
    ):
        netloc += f":{port}"
    path = parts.path or "/"
    if host == "t.me":
        path = re.sub(r"^/s/", "/", path)
        path = path.rstrip("/") or "/"
        # Channel usernames are case-insensitive.
        bits = path.split("/")
        if len(bits) > 1:
            bits[1] = bits[1].lower()
        path = "/".join(bits)
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in TRACKING and not k.lower().startswith("utm_")
        )
    )
    if host == "t.me":
        query = ""  # single message identity, including embed/preview query variations
    scheme = "https" if host == "t.me" else parts.scheme.lower()
    return urlunsplit((scheme, netloc, path, query, ""))


def clean_excerpt(text: str, limit: int = 600) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", text, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", text))).strip()[:limit]


def identity(source: str, original_url: str) -> str:
    return hashlib.sha256(f"{source}:{canonicalize(original_url)}".encode()).hexdigest()[:24]


def infer_type(title: str):
    from .models import ContentType

    text = title.casefold()
    rules = [
        (ContentType.BIG_PERSON_IDEA, ["altman", "amodei", "hassabis", "lecun", "huang", "musk"]),
        (ContentType.CAREER_SHIFT, ["job", "career", "salary", "layoff", "employment", "hiring"]),
        (ContentType.HUMAN_AI_STORY, ["teacher", "student", "family", "patient", "my life"]),
        (
            ContentType.DEVELOPER_STORY,
            ["i built", "my startup", "solo", "indie", "developer story"],
        ),
        (ContentType.BUSINESS_SIGNAL, ["funding", "revenue", "acqui", "startup", "business"]),
        (ContentType.OVERSEAS_DISCUSSION, ["ask hn", "debate", "discuss", "should we"]),
        (ContentType.AI_PRODUCT, ["model", "agent", "launch", "release", "gpt", "claude", "llm"]),
        (ContentType.TECH_SHIFT, ["ai", "robot", "research", "security", "technology"]),
    ]
    return next(
        (kind for kind, words in rules if any(w in text for w in words)),
        ContentType.INTERESTING_INTERNET,
    )


def normalize(raw: dict, labels: dict):
    from .models import ContentItem

    raw = dict(raw)
    raw["canonical_url"] = canonicalize(raw["canonical_url"])
    raw["title"] = clean_excerpt(raw["title"], 500) or "Untitled source reference"
    raw["raw_excerpt"] = clean_excerpt(raw.get("raw_excerpt", ""))
    raw["summary"] = raw["raw_excerpt"] or raw["title"]
    raw["content_type"] = infer_type(raw["title"])
    raw["id"] = identity(
        raw["source"], raw.get("metadata", {}).get("original_url", raw["canonical_url"])
    )
    label_type = raw["source_type"]
    if label_type.startswith("github"):
        label_type = "github"
    if (
        label_type == "telegram_bot"
        or raw.get("metadata", {}).get("original_platform") == "telegram"
    ):
        label_type = "telegram"
    raw["public_source_label"] = labels.get(label_type, "海外")
    return ContentItem(**raw)
