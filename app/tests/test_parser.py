from app.news.parser import parse_feed


def test_parse_feed_extracts_items() -> None:
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Feed</title>
        <item>
          <title>Новость 1</title>
          <link>https://example.com/1</link>
          <description>Описание</description>
          <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    items, etag, modified = parse_feed(content)
    assert len(items) == 1
    assert items[0].title == "Новость 1"
    assert items[0].link == "https://example.com/1"
    assert items[0].summary == "Описание"
    assert etag is None
    assert modified is None
