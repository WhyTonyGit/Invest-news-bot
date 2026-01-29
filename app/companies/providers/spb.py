from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from app.companies.models import Company
from app.companies.utils import build_aliases

LOGGER = logging.getLogger(__name__)


class SpbProvider:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "SPB"

    def _build_url(self) -> str:
        return f"{self.base_url}/md/v2/Securities"

    def _is_spb(self, payload: dict[str, Any]) -> bool:
        exchange = str(payload.get("exchange") or "").upper()
        board = str(payload.get("board") or "").upper()
        combined = f"{exchange} {board}"
        return "SPB" in combined or "SPBX" in combined

    async def fetch(self, session: aiohttp.ClientSession) -> list[Company]:
        url = self._build_url()
        async with session.get(url) as response:
            response.raise_for_status()
            payload = await response.json()
        if not isinstance(payload, list):
            LOGGER.warning("Unexpected SPB payload format: %s", type(payload))
            return []
        companies: list[Company] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if not ("exchange" in item or "board" in item):
                LOGGER.info("SPB item missing exchange/board fields, skipping: %s", item.get("symbol"))
                continue
            if not self._is_spb(item):
                continue
            ticker = str(item.get("symbol") or item.get("ticker") or "").strip()
            if not ticker:
                continue
            name = str(item.get("name") or item.get("shortName") or ticker).strip()
            isin = item.get("isin")
            companies.append(
                Company(
                    exchange="SPB",
                    ticker=ticker,
                    name=name,
                    isin=isin,
                    type=item.get("type"),
                    currency=item.get("currency"),
                    aliases=build_aliases(ticker, name),
                    source={"provider": "ALOR", "url": url},
                    updated_at=datetime.now(timezone.utc),
                )
            )
        LOGGER.info("SPB provider loaded %s companies", len(companies))
        return companies
