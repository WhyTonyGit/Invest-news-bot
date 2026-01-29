from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PreparedNews:
    title: str
    summary: str | None
    url: str
    published_at: datetime
    source_name: str
    mentions: dict[str, int]
    canonical_hash: str
