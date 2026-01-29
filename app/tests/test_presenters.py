from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.news.models import PreparedNews
from app.news.presenters import build_news_text


def test_build_news_text() -> None:
    news = PreparedNews(
        title="Лукойл обновил прогноз",
        summary="Подробности сделки",
        url="https://example.com",
        published_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_name="Test",
        mentions={"LKOH": 3},
        canonical_hash="hash",
    )

    text = build_news_text(news, ZoneInfo("Europe/Moscow"))

    assert "Лукойл" in text
    assert "#LKOH" in text
    assert "Источник: Test" in text
