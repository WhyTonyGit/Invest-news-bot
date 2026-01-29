from __future__ import annotations

import logging
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

    @property
    def name(self) -> str:
        return "MOEX"

    def _build_url(self) -> str:
        return f"{self.base_url}/engines/stock/markets/shares/securities.json"

    async def fetch(self, session: aiohttp.ClientSession) -> list[Company]:
        url = self._build_url()
        start = 0
        companies: list[Company] = []
        while True:
            params = {
                "iss.meta": "off",
                "start": start,
                "limit": self.page_size,
                "securities.columns": "SECID,SHORTNAME,NAME,ISIN,TYPE,CURRENCY",
            }
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                payload = await response.json()
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
        LOGGER.info("MOEX provider loaded %s companies", len(companies))
        return companies
