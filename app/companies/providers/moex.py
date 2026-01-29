from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp

from app.companies.models import Company
from app.companies.utils import build_aliases

LOGGER = logging.getLogger(__name__)


class MoexProvider:
    def __init__(self, base_url: str, page_size: int = 100) -> None:
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self._timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        self._max_total_seconds = 25.0

    @property
    def name(self) -> str:
        return "MOEX"

    def _build_url(self) -> str:
        return f"{self.base_url}/engines/stock/markets/shares/securities.json"

    def _create_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(timeout=self._timeout, trust_env=True)

    async def fetch(self, session: aiohttp.ClientSession | None = None) -> list[Company]:
        url = self._build_url()
        start = 0
        companies: list[Company] = []
        owns_session = session is None
        if session is None:
            session = self._create_session()
        LOGGER.info(
            "MOEX fetch start url=%s timeout=%s trust_env=%s",
            url,
            getattr(session, "timeout", None),
            getattr(session, "_trust_env", None),
        )
        deadline = time.monotonic() + self._max_total_seconds
        retries = 2
        try:
            while True:
                params = {
                    "iss.meta": "off",
                    "start": start,
                    "limit": self.page_size,
                    "securities.columns": "SECID,SHORTNAME,NAME,ISIN,TYPE,CURRENCY",
                }
                attempt = 0
                while True:
                    try:
                        async with session.get(url, params=params) as response:
                            response.raise_for_status()
                            payload = await response.json()
                        break
                    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                        if attempt >= retries:
                            raise
                        backoff = 0.5 if attempt == 0 else 1.0
                        LOGGER.warning("MOEX fetch attempt %s failed: %s", attempt + 1, exc)
                        await asyncio.sleep(backoff)
                        attempt += 1

                securities = payload.get("securities", {})
                columns: list[str] = securities.get("columns", [])
                data: list[list[Any]] = securities.get("data", [])
                if not data:
                    break
                for row in data:
                    row_dict = {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
                    ticker = str(row_dict.get("SECID") or "").strip()
                    if not ticker:
                        continue
                    short_name = str(row_dict.get("SHORTNAME") or "").strip()
                    full_name = str(row_dict.get("NAME") or "").strip()
                    name = (short_name or full_name or ticker).strip()
                    isin = row_dict.get("ISIN")
                    company_type = row_dict.get("TYPE")
                    currency = row_dict.get("CURRENCY")
                    aliases = build_aliases(ticker, name)
                    if full_name and full_name != name:
                        for alias in build_aliases(ticker, full_name):
                            if alias not in aliases:
                                aliases.append(alias)
                    companies.append(
                        Company(
                            exchange="MOEX",
                            ticker=ticker,
                            name=name,
                            isin=isin,
                            type=company_type,
                            currency=currency,
                            aliases=aliases,
                            source={"provider": "MOEX", "url": url},
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                if len(data) < self.page_size:
                    break
                start += self.page_size
                if time.monotonic() > deadline:
                    LOGGER.warning("MOEX fetch exceeded max total time, stopping pagination")
                    break
        finally:
            if owns_session:
                await session.close()
        LOGGER.info("MOEX provider loaded %s companies", len(companies))
        return companies
