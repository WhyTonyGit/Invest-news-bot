import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Base
from app.db.repo import add_subscription, ensure_user, list_subscriptions, remove_subscription
from app.db.session import create_engine, create_sessionmaker


@pytest.fixture
async def sessionmaker() -> async_sessionmaker:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return create_sessionmaker(engine)


@pytest.mark.asyncio
async def test_user_subscription_crud(sessionmaker: async_sessionmaker) -> None:
    async with sessionmaker() as session:
        await ensure_user(session, 1, True, "23:00-07:00", 60, 3, 20)

    async with sessionmaker() as session:
        added = await add_subscription(session, 1, "SBER")
        assert added is True

    async with sessionmaker() as session:
        subs = await list_subscriptions(session, 1)
        assert [sub.ticker for sub in subs] == ["SBER"]

    async with sessionmaker() as session:
        await remove_subscription(session, 1, "SBER")

    async with sessionmaker() as session:
        subs = await list_subscriptions(session, 1)
        assert subs == []
