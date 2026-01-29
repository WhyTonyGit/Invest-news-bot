from __future__ import annotations

from zoneinfo import ZoneInfo

from app.news.models import PreparedNews


def build_news_text(news: PreparedNews, tz: ZoneInfo) -> str:
    companies = " ".join(f"#{ticker}" for ticker in news.mentions.keys())
    published = news.published_at.astimezone(tz).strftime("%H:%M МСК")
    summary = (news.summary or "").strip()
    summary_line = (summary[:200] + "...") if summary else ""
    return (
        f"<b>{news.title}</b>\n"
        f"{summary_line}\n"
        f"Компании: {companies}\n"
        f"Источник: {news.source_name}\n"
        f"Время: {published}"
    )
