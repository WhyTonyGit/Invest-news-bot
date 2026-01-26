from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class FetchResult:
    content: str | None
    etag: str | None
    last_modified: str | None
    status: int


class FeedFetcher:
    def __init__(self, timeout: int, concurrency: int) -> None:
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency)

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        headers: dict[str, str] = {
            "User-Agent": "InvestNewsBot/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        async with self.semaphore:
            try:
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 304:
                        return FetchResult(None, response.headers.get("ETag"), response.headers.get("Last-Modified"), 304)
                    content = await response.text()
                    return FetchResult(
                        content,
                        response.headers.get("ETag"),
                        response.headers.get("Last-Modified"),
                        response.status,
                    )
            except asyncio.TimeoutError:
                return FetchResult(None, etag, last_modified, 408)
            except aiohttp.ClientError:
                return FetchResult(None, etag, last_modified, 500)
