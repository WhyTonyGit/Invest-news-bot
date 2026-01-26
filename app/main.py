from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.handlers import router
from app.config import BASE_DIR, load_settings
from app.db.models import Base, FeedSource
from app.db.repo import upsert_sources
from app.db.session import create_engine, create_sessionmaker
from app.news.fetcher import FeedFetcher
from app.news.matcher import CompanyMatcher
from app.news.scheduler import NewsScheduler
from app.news.sources import DEFAULT_SOURCES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("main")


async def prepare_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def build_sources() -> list[FeedSource]:
    return [FeedSource(name=source.name, url=source.url, enabled=True) for source in DEFAULT_SOURCES]


def ensure_sqlite_path(db_url: str) -> None:
    if not db_url.startswith("sqlite"):
        return
    parsed = urlparse(db_url)
    if not parsed.path:
        return
    db_path = Path(parsed.path)
    db_file = db_path if db_path.is_absolute() else Path.cwd() / db_path
    db_file.parent.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    settings = load_settings()
    ensure_sqlite_path(settings.db_url)
    engine = create_engine(settings.db_url)
    sessionmaker = create_sessionmaker(engine)
    await prepare_database(engine)

    async with sessionmaker() as session:
        await upsert_sources(session, build_sources())

    bot = Bot(settings.bot_token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    dp["sessionmaker"] = sessionmaker
    dp["companies_path"] = str(BASE_DIR / "data" / "companies_ru.json")
    dp["default_notifications_enabled"] = settings.default_notifications_enabled
    dp["default_quiet_hours"] = settings.default_quiet_hours
    dp["default_poll_seconds"] = settings.default_poll_seconds
    dp["default_match_threshold"] = settings.default_match_threshold
    dp["default_hourly_limit"] = settings.default_hourly_limit

    matcher = CompanyMatcher(Path(dp["companies_path"]))
    fetcher = FeedFetcher(settings.request_timeout, settings.fetch_concurrency)
    scheduler = NewsScheduler(matcher, sessionmaker, fetcher, bot)

    async def poll_news() -> None:
        try:
            await scheduler.run_once()
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed to poll news: %s", exc)

    scheduler_engine = AsyncIOScheduler()
    scheduler_engine.add_job(poll_news, "interval", seconds=settings.default_poll_seconds)
    scheduler_engine.start()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(dp.stop_polling()))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler_engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
