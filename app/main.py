from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.handlers import router
from app.bot.middlewares import DatabaseMiddleware
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


async def main() -> None:
    settings = load_settings()
    engine = create_engine(settings.db_url)
    sessionmaker = create_sessionmaker(engine)
    await prepare_database(engine)

    async with sessionmaker() as session:
        await upsert_sources(session, build_sources())

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    companies_path = str(BASE_DIR / "data" / "companies_ru.json")
    dp.update.middleware(DatabaseMiddleware(sessionmaker, settings, companies_path))
    LOGGER.info("DatabaseMiddleware enabled; sessionmaker injected into handlers.")

    matcher = CompanyMatcher(Path(companies_path))
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
