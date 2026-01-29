from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    default_poll_seconds: int
    default_notifications_enabled: bool
    default_quiet_hours: str
    default_match_threshold: int
    default_hourly_limit: int
    sources_refresh_minutes: int
    request_timeout: int
    fetch_concurrency: int
    companies_refresh_ttl_hours: int
    moex_iss_base_url: str
    alor_base_url: str
    companies_cache_backend: str
    companies_cache_path: str
    companies_fallback_path: str


def load_settings() -> Settings:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
    bot_token = (bot_token or "").strip()
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    return Settings(
        bot_token=bot_token,
        db_url=os.environ.get("DB_URL", "sqlite+aiosqlite:///./app.db"),
        default_poll_seconds=int(os.environ.get("DEFAULT_POLL_SECONDS", "60")),
        default_notifications_enabled=os.environ.get("DEFAULT_NOTIFICATIONS_ENABLED", "true").lower()
        == "true",
        default_quiet_hours=os.environ.get("DEFAULT_QUIET_HOURS", "23:00-07:00"),
        default_match_threshold=int(os.environ.get("DEFAULT_MATCH_THRESHOLD", "3")),
        default_hourly_limit=int(os.environ.get("DEFAULT_HOURLY_LIMIT", "20")),
        sources_refresh_minutes=int(os.environ.get("SOURCES_REFRESH_MINUTES", "60")),
        request_timeout=int(os.environ.get("REQUEST_TIMEOUT", "15")),
        fetch_concurrency=int(os.environ.get("FETCH_CONCURRENCY", "5")),
        companies_refresh_ttl_hours=int(os.environ.get("COMPANIES_REFRESH_TTL_HOURS", "24")),
        moex_iss_base_url=os.environ.get("MOEX_ISS_BASE_URL", "https://iss.moex.com/iss"),
        alor_base_url=os.environ.get("ALOR_BASE_URL", "https://api.alor.ru"),
        companies_cache_backend=os.environ.get("COMPANIES_CACHE_BACKEND", "file"),
        companies_cache_path=os.environ.get(
            "COMPANIES_CACHE_PATH", str(BASE_DIR / "data" / "companies_cache.json")
        ),
        companies_fallback_path=os.environ.get(
            "COMPANIES_FALLBACK_PATH", str(BASE_DIR / "data" / "companies_ru.json")
        ),
    )
