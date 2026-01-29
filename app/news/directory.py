from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import aiohttp
from rapidfuzz import process

from app.utils.normalize import normalize_text

LOGGER = logging.getLogger("news.directory")


@dataclass(frozen=True)
class Company:
    exchange: str
    ticker: str
    name: str
    isin: str | None
    type: str | None
    currency: str | None
    aliases: list[str]
    source: dict[str, Any]
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange": self.exchange,
            "ticker": self.ticker,
            "name": self.name,
            "isin": self.isin,
            "type": self.type,
            "currency": self.currency,
            "aliases": self.aliases,
            "source": self.source,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class RefreshResult:
    updated: bool
    count: int
    error: str | None = None


class CompanyProvider:
    async def fetch(self) -> list[Company]:
        raise NotImplementedError


class MOEXProvider(CompanyProvider):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch(self) -> list[Company]:
        return await _fetch_moex_securities(self.base_url)


class AlorSPBProvider(CompanyProvider):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch(self) -> list[Company]:
        url = f"{self.base_url}/md/v2/Securities"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                payload = await response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            return []
        records: list[Company] = []
        for item in data:
            if not _is_spb(item):
                continue
            ticker = str(item.get("symbol") or item.get("ticker") or item.get("code") or "").upper()
            if not ticker:
                continue
            name = str(item.get("shortName") or item.get("name") or item.get("description") or ticker).strip()
            records.append(
                Company(
                    exchange="SPB",
                    ticker=ticker,
                    name=name,
                    isin=item.get("isin"),
                    type=item.get("type"),
                    currency=item.get("currency"),
                    aliases=_build_aliases(ticker, name, None),
                    source={"provider": "alor", "url": url},
                    updated_at=datetime.now(timezone.utc),
                )
            )
        return records


class CompanyDirectoryService:
    def __init__(
        self,
        providers: Iterable[CompanyProvider],
        cache_path: Path,
        ttl_hours: int,
        fallback_path: Path,
    ) -> None:
        self._providers = list(providers)
        self._cache_path = cache_path
        self._ttl = timedelta(hours=ttl_hours)
        self._fallback_path = fallback_path
        self._companies: list[Company] = []
        self._last_updated: datetime | None = None
        self._refresh_task: asyncio.Task | None = None

    async def startup(self) -> None:
        self._load_cache()
        if not self._companies:
            self._companies = self._load_fallback()
        if self._is_stale():
            self._refresh_task = asyncio.create_task(self.refresh(force=True))

    async def get_all(self) -> list[Company]:
        if not self._companies:
            await self.refresh(force=True)
        elif self._is_stale() and self._refresh_task is None:
            self._refresh_task = asyncio.create_task(self.refresh(force=True))
        return list(self._companies)

    async def get_by_ticker(self, exchange: str, ticker: str) -> Company | None:
        exchange = exchange.upper()
        ticker = ticker.upper()
        for company in await self.get_all():
            if company.exchange == exchange and company.ticker == ticker:
                return company
        return None

    async def search(self, query: str, limit: int = 5) -> list[Company]:
        query_norm = normalize_text(query)
        companies = await self.get_all()
        if not companies:
            LOGGER.debug("Company search requested but directory is empty")
        direct: list[Company] = []
        for company in companies:
            if query_norm == normalize_text(company.ticker):
                return [company]
            if any(query_norm in normalize_text(alias) for alias in company.aliases):
                direct.append(company)
        if direct:
            return direct[:limit]
        choices = {company.ticker: " ".join(company.aliases) for company in companies}
        matches = process.extract(query_norm, choices, limit=limit)
        results = [next(c for c in companies if c.ticker == ticker) for ticker, score, _ in matches if score > 60]
        if not results:
            LOGGER.debug("Company search returned no matches for query=%s", query)
        return results

    async def refresh(self, force: bool = False) -> RefreshResult:
        if not force and not self._is_stale():
            return RefreshResult(updated=False, count=len(self._companies))
        records: list[Company] = []
        errors: list[str] = []
        for provider in self._providers:
            try:
                provider_records = await provider.fetch()
                LOGGER.debug("Provider %s returned %s records", provider.__class__.__name__, len(provider_records))
                records.extend(provider_records)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Provider %s failed: %s", provider.__class__.__name__, exc)
                errors.append(str(exc))

        if records:
            merged = _merge_companies(records)
            self._companies = merged
            self._last_updated = datetime.now(timezone.utc)
            self._save_cache()
            self._log_refresh_summary(records, merged)
            self._refresh_task = None
            return RefreshResult(updated=True, count=len(self._companies), error="; ".join(errors) or None)

        if not self._companies:
            self._companies = self._load_fallback()
        self._refresh_task = None
        return RefreshResult(updated=False, count=len(self._companies), error="; ".join(errors) or None)

    def _log_refresh_summary(self, records: list[Company], merged: list[Company]) -> None:
        moex_count = sum(1 for company in records if company.exchange == "MOEX")
        spb_count = sum(1 for company in records if company.exchange == "SPB")
        LOGGER.info(
            "Company directory refreshed: MOEX=%s SPB=%s merged=%s",
            moex_count,
            spb_count,
            len(merged),
        )

    def _is_stale(self) -> bool:
        if not self._last_updated:
            return True
        return datetime.now(timezone.utc) - self._last_updated > self._ttl

    def _load_cache(self) -> None:
        if not self._cache_path.exists():
            return
        payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        self._last_updated = _parse_datetime(payload.get("updated_at"))
        companies = payload.get("companies", [])
        self._companies = _load_companies_from_payload(companies)

    def _save_cache(self) -> None:
        payload = {
            "updated_at": (self._last_updated or datetime.now(timezone.utc)).isoformat(),
            "companies": [company.to_dict() for company in self._companies],
        }
        self._cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_fallback(self) -> list[Company]:
        if not self._fallback_path.exists():
            return []
        payload = json.loads(self._fallback_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            companies: list[Company] = []
            now = datetime.now(timezone.utc)
            for ticker, aliases in payload.items():
                companies.append(
                    Company(
                        exchange="MOEX",
                        ticker=ticker,
                        name=aliases[0] if aliases else ticker,
                        isin=None,
                        type=None,
                        currency=None,
                        aliases=aliases,
                        source={"provider": "fallback", "url": None},
                        updated_at=now,
                    )
                )
            return companies
        if isinstance(payload, list):
            return _load_companies_from_payload(payload)
        return []


def _map_type(secname: str | None) -> str | None:
    if not secname:
        return None
    normalized = str(secname).lower()
    if "etf" in normalized or "паи" in normalized:
        return "etf"
    if "депозитар" in normalized or "dr" in normalized:
        return "depositary_receipt"
    if "облигац" in normalized:
        return "bond"
    return "share"


def _normalize_alias(name: str) -> str:
    return name.replace("\"", "").replace("«", "").replace("»", "").strip()


def _build_aliases(ticker: str, name: str, extra: str | None) -> list[str]:
    aliases = {
        ticker,
        f"${ticker}",
        name,
        _normalize_alias(name),
        name.lower(),
    }
    if extra:
        aliases.add(extra)
    return sorted({alias for alias in aliases if alias})


def _is_spb(item: dict[str, Any]) -> bool:
    exchange = str(item.get("exchange") or item.get("board") or item.get("market") or "").upper()
    return exchange in {"SPB", "SPBX"} or "SPB" in exchange


def _merge_companies(records: list[Company]) -> list[Company]:
    merged: dict[tuple[str, str], Company] = {}
    for company in records:
        key = (company.exchange, company.ticker)
        if key in merged:
            existing = merged[key]
            aliases = sorted({*existing.aliases, *company.aliases})
            merged[key] = Company(
                exchange=company.exchange,
                ticker=company.ticker,
                name=company.name or existing.name,
                isin=company.isin or existing.isin,
                type=company.type or existing.type,
                currency=company.currency or existing.currency,
                aliases=aliases,
                source=company.source,
                updated_at=company.updated_at,
            )
        else:
            merged[key] = company
    return list(merged.values())


async def _fetch_moex_securities(base_url: str) -> list[Company]:
    url = f"{base_url.rstrip('/')}/engines/stock/markets/shares/securities.json"
    records: list[Company] = []
    start = 0
    params = {
        "iss.meta": "off",
        "iss.only": "securities",
        "securities.columns": "SECID,SHORTNAME,NAME,ISIN,SECNAME,CURRENCY,FACEUNIT,BOARDID",
    }
    async with aiohttp.ClientSession() as session:
        while True:
            page_params = {**params, "start": str(start)}
            async with session.get(url, params=page_params) as response:
                response.raise_for_status()
                payload = await response.json()
            data = payload.get("securities", {})
            items = data.get("data", [])
            columns = data.get("columns", [])
            if not items:
                break
            for row in items:
                row_map = dict(zip(columns, row))
                ticker = str(row_map.get("SECID", "")).upper().strip()
                if not ticker:
                    continue
                name = str(row_map.get("SHORTNAME") or row_map.get("NAME") or ticker).strip()
                secname = row_map.get("SECNAME")
                company = Company(
                    exchange="MOEX",
                    ticker=ticker,
                    name=name,
                    isin=row_map.get("ISIN"),
                    type=_map_type(secname),
                    currency=row_map.get("CURRENCY") or row_map.get("FACEUNIT"),
                    aliases=_build_aliases(ticker, name, None),
                    source={"provider": "moex_iss", "url": str(response.url)},
                    updated_at=datetime.now(timezone.utc),
                )
                records.append(company)
            start += len(items)
    return records


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_companies_from_payload(payload: list[dict[str, Any]]) -> list[Company]:
    companies: list[Company] = []
    for item in payload:
        companies.append(
            Company(
                exchange=item["exchange"],
                ticker=item["ticker"],
                name=item["name"],
                isin=item.get("isin"),
                type=item.get("type"),
                currency=item.get("currency"),
                aliases=list(item.get("aliases", [])),
                source=item.get("source", {}),
                updated_at=_parse_datetime(item.get("updated_at")) or datetime.now(timezone.utc),
            )
        )
    return companies
