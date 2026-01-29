from app.news.presenter import SourceRef, build_news_message, format_sources


def test_format_sources_empty() -> None:
    assert format_sources([]) == "—"


def test_build_news_message() -> None:
    sources = [SourceRef(name="Источник", url="https://example.com")]
    text = build_news_message(
        title="Заголовок",
        summary_line="TL;DR",
        companies="#SBER",
        category="EARNINGS",
        impact=5,
        sources=sources,
        published="12:00 МСК",
    )
    assert "Заголовок" in text
    assert "TL;DR" in text
    assert "Категория: EARNINGS" in text
    assert "Источник" in text
