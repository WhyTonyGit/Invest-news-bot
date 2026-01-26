from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Delivery, FeedSource, FeedState, NewsItem, NewsMention, Subscription, User


async def ensure_user(
    session: AsyncSession,
    tg_id: int,
    default_notifications_enabled: bool,
    default_quiet_hours: str,
    default_polling_interval: int,
    default_match_threshold: int,
    default_hourly_limit: int,
) -> User:
    user = await session.get(User, tg_id)
    if user:
        return user
    user = User(
        tg_id=tg_id,
        notifications_enabled=default_notifications_enabled,
        quiet_hours=default_quiet_hours,
        polling_interval=default_polling_interval,
        match_threshold=default_match_threshold,
        hourly_limit=default_hourly_limit,
    )
    session.add(user)
    await session.commit()
    return user


async def list_subscriptions(session: AsyncSession, tg_id: int) -> list[Subscription]:
    result = await session.execute(select(Subscription).where(Subscription.tg_id == tg_id))
    return list(result.scalars().all())


async def add_subscription(session: AsyncSession, tg_id: int, ticker: str) -> bool:
    sub = Subscription(tg_id=tg_id, ticker=ticker)
    session.add(sub)
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False


async def remove_subscription(session: AsyncSession, tg_id: int, ticker: str) -> None:
    await session.execute(
        delete(Subscription).where(Subscription.tg_id == tg_id, Subscription.ticker == ticker)
    )
    await session.commit()


async def clear_subscriptions(session: AsyncSession, tg_id: int) -> None:
    await session.execute(delete(Subscription).where(Subscription.tg_id == tg_id))
    await session.commit()


async def set_notifications(session: AsyncSession, tg_id: int, enabled: bool) -> None:
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(notifications_enabled=enabled)
    )
    await session.commit()


async def update_settings(
    session: AsyncSession,
    tg_id: int,
    polling_interval: int | None = None,
    quiet_hours: str | None = None,
    match_threshold: int | None = None,
    hourly_limit: int | None = None,
) -> None:
    values: dict[str, object] = {}
    if polling_interval is not None:
        values["polling_interval"] = polling_interval
    if quiet_hours is not None:
        values["quiet_hours"] = quiet_hours
    if match_threshold is not None:
        values["match_threshold"] = match_threshold
    if hourly_limit is not None:
        values["hourly_limit"] = hourly_limit
    if not values:
        return
    await session.execute(update(User).where(User.tg_id == tg_id).values(**values))
    await session.commit()


async def upsert_sources(session: AsyncSession, sources: Iterable[FeedSource]) -> None:
    existing = await session.execute(select(FeedSource.url))
    existing_urls = {row[0] for row in existing.all()}
    for source in sources:
        if source.url in existing_urls:
            continue
        session.add(source)
    await session.commit()


async def list_enabled_sources(session: AsyncSession) -> list[FeedSource]:
    result = await session.execute(select(FeedSource).where(FeedSource.enabled.is_(True)))
    return list(result.scalars().all())


async def get_feed_state(session: AsyncSession, source_id: int) -> FeedState | None:
    return await session.get(FeedState, source_id)


async def update_feed_state(
    session: AsyncSession,
    source_id: int,
    etag: str | None,
    last_modified: str | None,
    last_item_ts: datetime | None,
) -> None:
    now = datetime.now(timezone.utc)
    state = await session.get(FeedState, source_id)
    if state is None:
        state = FeedState(
            source_id=source_id,
            etag=etag,
            last_modified=last_modified,
            last_checked_at=now,
            last_item_ts=last_item_ts,
        )
        session.add(state)
    else:
        state.etag = etag
        state.last_modified = last_modified
        state.last_checked_at = now
        if last_item_ts:
            state.last_item_ts = last_item_ts
    await session.commit()


async def store_news_item(
    session: AsyncSession,
    canonical_hash: str,
    title: str,
    url: str,
    published_at: datetime,
    source_id: int,
    summary: str | None,
    raw: str | None,
) -> NewsItem | None:
    news = NewsItem(
        canonical_hash=canonical_hash,
        title=title,
        url=url,
        published_at=published_at,
        source_id=source_id,
        summary=summary,
        raw=raw,
    )
    session.add(news)
    try:
        await session.commit()
        return news
    except IntegrityError:
        await session.rollback()
        return None


async def store_mentions(session: AsyncSession, news_id: int, mentions: dict[str, int]) -> None:
    for ticker, score in mentions.items():
        mention = NewsMention(news_id=news_id, ticker=ticker, score=score)
        session.add(mention)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def list_users_for_delivery(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.notifications_enabled.is_(True)))
    return list(result.scalars().all())


async def has_delivery(session: AsyncSession, news_id: int, tg_id: int) -> bool:
    result = await session.execute(
        select(Delivery).where(Delivery.news_id == news_id, Delivery.tg_id == tg_id)
    )
    return result.scalar_one_or_none() is not None


async def store_delivery(session: AsyncSession, news_id: int, tg_id: int) -> None:
    delivery = Delivery(news_id=news_id, tg_id=tg_id)
    session.add(delivery)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def purge_old_news(session: AsyncSession, days: int = 7) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    await session.execute(delete(NewsItem).where(NewsItem.published_at < cutoff))
    await session.execute(delete(Delivery).where(Delivery.delivered_at < cutoff))
    await session.commit()


async def count_hourly_deliveries(session: AsyncSession, tg_id: int) -> int:
    now = datetime.now(timezone.utc)
    window = now - timedelta(hours=1)
    result = await session.execute(
        select(func.count(Delivery.id)).where(
            Delivery.tg_id == tg_id, Delivery.delivered_at >= window
        )
    )
    return int(result.scalar_one())
