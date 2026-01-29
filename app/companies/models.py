from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Company:
    exchange: str
    ticker: str
    name: str
    isin: str | None
    type: str | None
    currency: str | None
    aliases: list[str]
    source: dict[str, Any]
    updated_at: datetime


@dataclass(frozen=True)
class RefreshResult:
    companies: list[Company]
    updated_at: datetime | None
    from_cache: bool
    used_fallback: bool
    errors: list[str]
