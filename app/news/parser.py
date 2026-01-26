from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import feedparser


@dataclass(frozen=True)
class ParsedItem:
    title: str
    link: str
    summary: str | None
    published: datetime
    raw: str | None


def _parse_datetime(entry: dict[str, Any]) -> datetime:
    if entry.get("published_parsed"):
        return datetime(*entry["published_parsed"][:6], tzinfo=timezone.utc)
    if entry.get("updated_parsed"):
        return datetime(*entry["updated_parsed"][:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def parse_feed(content: str) -> tuple[list[ParsedItem], str | None, str | None]:
    parsed = feedparser.parse(content)
    etag = parsed.get("etag")
    modified = parsed.get("modified")
    items: list[ParsedItem] = []
    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        summary = entry.get("summary", "") or entry.get("description", "")
        summary = summary.strip() if summary else None
        published = _parse_datetime(entry)
        items.append(
            ParsedItem(
                title=title,
                link=link,
                summary=summary,
                published=published,
                raw=entry.get("summary", None),
            )
        )
    return items, etag, modified
