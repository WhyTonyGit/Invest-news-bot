import pytest

from app.db.models import Base
from app.db.repo import (
    add_subscription,
    ensure_user,
    get_user_settings,
    list_subscriptions,
    set_feed_mode,
)
from app.db.session import create_engine, create_sessionmaker


@pytest.mark.asyncio
async def test_repo_user_and_settings() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = create_sessionmaker(engine)

    async with sessionmaker() as session:
        user = await ensure_user(
            session,
            tg_id=1,
            default_notifications_enabled=True,
            default_quiet_hours="23:00-07:00",
            default_polling_interval=60,
            default_match_threshold=3,
            default_hourly_limit=20,
            default_feed_mode="watchlist",
            default_digest_frequency="daily",
            default_summary_enabled=True,
        )
        assert user.tg_id == 1

    async with sessionmaker() as session:
        settings = await get_user_settings(session, 1)
        assert settings is not None
        await set_feed_mode(session, 1, "market")

    async with sessionmaker() as session:
        settings = await get_user_settings(session, 1)
        assert settings.feed_mode == "market"


@pytest.mark.asyncio
async def test_repo_subscriptions() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = create_sessionmaker(engine)

    async with sessionmaker() as session:
        await ensure_user(
            session,
            tg_id=2,
            default_notifications_enabled=True,
            default_quiet_hours="23:00-07:00",
            default_polling_interval=60,
            default_match_threshold=3,
            default_hourly_limit=20,
            default_feed_mode="watchlist",
            default_digest_frequency="daily",
            default_summary_enabled=True,
        )

    async with sessionmaker() as session:
        added = await add_subscription(session, 2, "SBER")
        assert added is True

    async with sessionmaker() as session:
        subs = await list_subscriptions(session, 2)
        assert len(subs) == 1
        assert subs[0].ticker == "SBER"
