from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import aiohttp

from app.bot.keyboards import market_notification_keyboard, notification_keyboard
from app.db.repo import (
    add_cluster_member,
    count_hourly_deliveries,
    get_cached_summary,
    get_feed_state,
    get_user_settings,
    has_delivery,
    list_enabled_sources,
    list_subscriptions,
    list_users_for_delivery,
    set_cluster_representative,
    store_cluster,
    store_delivery,
    store_mentions,
    store_news_item,
    store_summary_cache,
    update_feed_state,
)
from app.news.dedupe import canonical_hash
from app.news.fetcher import FeedFetcher
from app.news.matcher import CompanyMatcher
from app.news.parser import parse_feed
from app.news.presenter import SourceRef, build_news_message
from app.news.service import NewsCandidate, NewsCluster, NewsService, impact_score
from app.news.summary import SummaryService

LOGGER = logging.getLogger("news.scheduler")


@dataclass
class PreparedNews:
    title: str
    summary: str | None
    url: str
    published_at: datetime
    source_name: str
    source_id: int
    mentions: dict[str, int]
    canonical_hash: str
    category: str
    sources: list[tuple[str, str, int]]


class NewsScheduler:
    def __init__(
        self,
        matcher: CompanyMatcher,
        sessionmaker,
        fetcher: FeedFetcher,
        bot,
        summary_service: SummaryService,
        directory,
        tz_name: str = "Europe/Moscow",
    ) -> None:
        self.matcher = matcher
        self.service = NewsService(matcher)
        self.sessionmaker = sessionmaker
        self.fetcher = fetcher
        self.bot = bot
        self.summary_service = summary_service
        self.directory = directory
        self.tz = ZoneInfo(tz_name)

    async def run_once(self) -> None:
        companies = await self.directory.get_all()
        self.matcher.update(companies)
        async with self.sessionmaker() as session:
            sources = await list_enabled_sources(session)
        if not sources:
            LOGGER.warning("No sources enabled")
            return

        async with aiohttp.ClientSession() as http_session:
            tasks = [self._fetch_source(http_session, source) for source in sources]
            results = await asyncio.gather(*tasks)

        candidates: list[NewsCandidate] = []
        for result in results:
            if result is None:
                continue
            source, items, etag_new, modified_new, latest_ts, last_item_ts = result
            await self._update_state(source.id, etag_new, modified_new, latest_ts)
            candidates.extend(
                self.service.prepare_candidates(
                    items,
                    source.name,
                    source.id,
                    last_item_ts=last_item_ts,
                    require_mentions=False,
                )
            )

        clusters = self.service.cluster(candidates)
        for cluster in clusters:
            prepared = self._prepare_cluster(cluster)
            await self._store_and_deliver(prepared)

    async def _fetch_source(self, http_session: aiohttp.ClientSession, source):
        async with self.sessionmaker() as session:
            state = await get_feed_state(session, source.id)
        etag = state.etag if state else None
        last_modified = state.last_modified if state else None

        result = await self.fetcher.fetch(http_session, source.url, etag, last_modified)
        if result.status == 304 or not result.content:
            await self._update_state(source.id, result.etag, result.last_modified, None)
            return None
        items, etag_new, modified_new = parse_feed(result.content)
        latest_ts: datetime | None = None
        for item in items:
            latest_ts = max(latest_ts or item.published, item.published)
        return source, items, etag_new or result.etag, modified_new or result.last_modified, latest_ts, (
            state.last_item_ts if state else None
        )

    async def _update_state(
        self, source_id: int, etag: str | None, last_modified: str | None, latest_ts: datetime | None
    ) -> None:
        async with self.sessionmaker() as session:
            await update_feed_state(session, source_id, etag, last_modified, latest_ts)

    def _prepare_cluster(self, cluster: NewsCluster) -> PreparedNews:
        representative = sorted(cluster.items, key=lambda item: item.published_at, reverse=True)[0]
        sources = [(item.source_name, item.url, item.source_id) for item in cluster.items]
        return PreparedNews(
            title=representative.title,
            summary=representative.summary,
            url=representative.url,
            published_at=representative.published_at,
            source_name=representative.source_name,
            source_id=representative.source_id,
            mentions=representative.mentions,
            canonical_hash=representative.canonical_hash,
            category=representative.category,
            sources=sources,
        )

    async def _store_and_deliver(self, news: PreparedNews) -> None:
        async with self.sessionmaker() as session:
            cluster = await store_cluster(session, news.category)
        stored_items: list[int] = []
        for _, source_url, source_id in news.sources:
            async with self.sessionmaker() as session:
                stored = await store_news_item(
                    session,
                    canonical_hash(news.title, news.summary, source_url),
                    news.title,
                    source_url,
                    news.published_at,
                    source_id=source_id,
                    summary=news.summary,
                    raw=None,
                )
                if stored is None:
                    continue
                stored_items.append(stored.id)
                if news.mentions:
                    await store_mentions(session, stored.id, news.mentions)
                await add_cluster_member(session, cluster.id, stored.id)
        if stored_items:
            async with self.sessionmaker() as session:
                await set_cluster_representative(session, cluster.id, stored_items[0])
        await self._deliver_to_users(stored_items[0] if stored_items else None, news)

    async def _deliver_to_users(self, news_id: int | None, news: PreparedNews) -> None:
        async with self.sessionmaker() as session:
            users = await list_users_for_delivery(session)

        for user in users:
            async with self.sessionmaker() as session:
                settings = await get_user_settings(session, user.tg_id)
            feed_mode = settings.feed_mode if settings else "watchlist"
            if feed_mode == "watchlist":
                if not await self._user_should_receive(user, news.mentions):
                    continue
            if not self._check_quiet_hours(user.quiet_hours):
                continue
            if news_id is not None:
                async with self.sessionmaker() as session:
                    if await has_delivery(session, news_id, user.tg_id):
                        continue
            async with self.sessionmaker() as session:
                hourly_count = await count_hourly_deliveries(session, user.tg_id)
            if hourly_count >= user.hourly_limit:
                continue
            await self._send_news(user.tg_id, news, settings)
            if news_id is not None:
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

    async def _send_news(self, tg_id: int, news: PreparedNews, settings) -> None:
        companies = " ".join(f"#{ticker}" for ticker in news.mentions.keys()) or "—"
        published = news.published_at.astimezone(self.tz).strftime("%H:%M МСК")
        summary_line = ""
        if settings and settings.summary_enabled:
            summary_line = await self._get_or_build_summary(news)
        sources = [SourceRef(name=name, url=url) for name, url, _ in news.sources]
        text = build_news_message(
            title=news.title,
            summary_line=summary_line,
            companies=companies,
            category=news.category,
            impact=impact_score(news.category),
            sources=sources,
            published=published,
        )
        if news.mentions:
            for ticker in news.mentions.keys():
                await self.bot.send_message(
                    tg_id,
                    text,
                    reply_markup=notification_keyboard(news.url, ticker),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                break
        else:
            await self.bot.send_message(
                tg_id,
                text,
                reply_markup=market_notification_keyboard(news.url),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    async def _get_or_build_summary(self, news: PreparedNews) -> str:
        summary_text = news.summary or news.title
        content_hash = self.summary_service.hash_content(news.title, summary_text, news.url)
        async with self.sessionmaker() as session:
            cached = await get_cached_summary(session, content_hash)
        if cached:
            return cached.summary
        summary, facts, content_hash = await self.summary_service.build_summary(
            news.title, summary_text, news.url
        )
        async with self.sessionmaker() as session:
            await store_summary_cache(session, content_hash, summary, facts)
        return summary
