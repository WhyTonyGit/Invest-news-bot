import aiohttp
import pytest

pytest.importorskip("pytest_asyncio")
aioresponses = pytest.importorskip("aioresponses").aioresponses

from app.news.fetcher import FeedFetcher


@pytest.mark.asyncio
async def test_fetcher_handles_304() -> None:
    fetcher = FeedFetcher(timeout=5, concurrency=1)
    url = "https://example.com/feed"
    with aioresponses() as mocked:
        mocked.get(url, status=304, headers={"ETag": "abc"})
        async with aiohttp.ClientSession() as session:
            result = await fetcher.fetch(session, url, etag="abc")
    assert result.status == 304
    assert result.content is None


@pytest.mark.asyncio
async def test_fetcher_reads_content() -> None:
    fetcher = FeedFetcher(timeout=5, concurrency=1)
    url = "https://example.com/feed"
    with aioresponses() as mocked:
        mocked.get(url, status=200, body="feed", headers={"ETag": "new"})
        async with aiohttp.ClientSession() as session:
            result = await fetcher.fetch(session, url)
    assert result.status == 200
    assert result.content == "feed"
