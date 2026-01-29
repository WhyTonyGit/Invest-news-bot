from app.news.parser import parse_feed


def test_parse_feed_items() -> None:
    feed = """
    <rss version="2.0">
      <channel>
        <title>Test</title>
        <item>
          <title>News 1</title>
          <link>https://example.com/1</link>
          <description>Summary</description>
          <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    items, etag, modified = parse_feed(feed)

    assert len(items) == 1
    assert items[0].title == "News 1"
    assert items[0].link == "https://example.com/1"
    assert items[0].summary == "Summary"
    assert etag is None
    assert modified is None
