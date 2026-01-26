from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import aiohttp

from app.bot.keyboards import notification_keyboard
from app.db.repo import (
    count_hourly_deliveries,
    get_feed_state,
    has_delivery,
    list_enabled_sources,
    list_subscriptions,
    list_users_for_delivery,
    store_delivery,
    store_mentions,
    store_news_item,
    update_feed_state,
)
from app.news.dedupe import canonical_hash, is_similar
from app.news.fetcher import FeedFetcher
from app.news.matcher import CompanyMatcher
from app.news.parser import parse_feed

LOGGER = logging.getLogger("news.scheduler")


@dataclass
class PreparedNews:
    title: str
    summary: str | None
    url: str
    published_at: datetime
    source_name: str
    mentions: dict[str, int]
    canonical_hash: str


class NewsScheduler:
    def __init__(
        self,
        matcher: CompanyMatcher,
        sessionmaker,
        fetcher: FeedFetcher,
        bot,
        tz_name: str = "Europe/Moscow",
    ) -> None:
        self.matcher = matcher
        self.sessionmaker = sessionmaker
        self.fetcher = fetcher
        self.bot = bot
        self.tz = ZoneInfo(tz_name)
        self._recent_titles: list[str] = []

    async def run_once(self) -> None:
        async with self.sessionmaker() as session:
            sources = await list_enabled_sources(session)
        if not sources:
            LOGGER.warning("No sources enabled")
            return

        async with aiohttp.ClientSession() as http_session:
            tasks = [self._process_source(http_session, source) for source in sources]
            await asyncio.gather(*tasks)

    async def _process_source(self, http_session: aiohttp.ClientSession, source) -> None:
        async with self.sessionmaker() as session:
            state = await get_feed_state(session, source.id)
        etag = state.etag if state else None
        last_modified = state.last_modified if state else None

        result = await self.fetcher.fetch(http_session, source.url, etag, last_modified)
        if result.status == 304 or not result.content:
            await self._update_state(source.id, result.etag, result.last_modified, None)
            return
        items, etag_new, modified_new = parse_feed(result.content)
        latest_ts: datetime | None = None
        prepared: list[PreparedNews] = []
        for item in items:
            if state and state.last_item_ts and item.published <= state.last_item_ts:
                continue
            mentions = self.matcher.match(item.title, item.summary)
            if not mentions:
                continue
            hash_value = canonical_hash(item.title, item.summary)
            if self._is_recent_duplicate(item.title):
                continue
            prepared.append(
                PreparedNews(
                    title=item.title,
                    summary=item.summary,
                    url=item.link,
                    published_at=item.published,
                    source_name=source.name,
                    mentions=mentions,
                    canonical_hash=hash_value,
                )
            )
            latest_ts = max(latest_ts or item.published, item.published)

        await self._update_state(source.id, etag_new or result.etag, modified_new or result.last_modified, latest_ts)

        for news in prepared:
            await self._store_and_deliver(news, source.id)

    async def _update_state(
        self, source_id: int, etag: str | None, last_modified: str | None, latest_ts: datetime | None
    ) -> None:
        async with self.sessionmaker() as session:
            await update_feed_state(session, source_id, etag, last_modified, latest_ts)

    def _is_recent_duplicate(self, title: str) -> bool:
        for existing in self._recent_titles:
            if is_similar(title, existing, threshold=90):
                return True
        self._recent_titles.append(title)
        if len(self._recent_titles) > 200:
            self._recent_titles = self._recent_titles[-100:]
        return False

    async def _store_and_deliver(self, news: PreparedNews, source_id: int) -> None:
        async with self.sessionmaker() as session:
            stored = await store_news_item(
                session,
                news.canonical_hash,
                news.title,
                news.url,
                news.published_at,
                source_id,
                news.summary,
                None,
            )
            if stored is None:
                return
            await store_mentions(session, stored.id, news.mentions)

        await self._deliver_to_users(stored.id, news)

    async def _deliver_to_users(self, news_id: int, news: PreparedNews) -> None:
        async with self.sessionmaker() as session:
            users = await list_users_for_delivery(session)

        for user in users:
            if not await self._user_should_receive(user, news.mentions):
                continue
            if not self._check_quiet_hours(user.quiet_hours):
                continue
            async with self.sessionmaker() as session:
                if await has_delivery(session, news_id, user.tg_id):
                    continue
            async with self.sessionmaker() as session:
                hourly_count = await count_hourly_deliveries(session, user.tg_id)
            if hourly_count >= user.hourly_limit:
                continue
            await self._send_news(user.tg_id, news)
            async with self.sessionmaker() as session:
                await store_delivery(session, news_id, user.tg_id)

    async def _user_should_receive(self, user, mentions: dict[str, int]) -> bool:
        async with self.sessionmaker() as session:
            subs = await list_subscriptions(session, user.tg_id)
        subscribed = {sub.ticker for sub in subs}
        relevant = {
            ticker for ticker in subscribed.intersection(mentions.keys()) if mentions[ticker] >= user.match_threshold
        }
        return bool(relevant)

    def _check_quiet_hours(self, quiet_hours: str) -> bool:
        try:
            start_str, end_str = quiet_hours.split("-")
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)
        except ValueError:
            return True
        now = datetime.now(self.tz).time()
        if start < end:
            return not (start <= now <= end)
        return not (now >= start or now <= end)

    async def _send_news(self, tg_id: int, news: PreparedNews) -> None:
        companies = " ".join(f"#{ticker}" for ticker in news.mentions.keys())
        published = news.published_at.astimezone(self.tz).strftime("%H:%M МСК")
        summary = (news.summary or "").strip()
        summary_line = (summary[:200] + "...") if summary else ""
        text = (
            f"<b>{news.title}</b>\n"
            f"{summary_line}\n"
            f"Компании: {companies}\n"
            f"Источник: {news.source_name}\n"
            f"Время: {published}"
        )
        for ticker in news.mentions.keys():
            await self.bot.send_message(
                tg_id,
                text,
                reply_markup=notification_keyboard(news.url, ticker),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            break
