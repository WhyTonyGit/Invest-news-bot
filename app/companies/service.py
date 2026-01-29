from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import aiohttp
from rapidfuzz import process

from app.companies.models import Company, RefreshResult
from app.utils.normalize import normalize_text

LOGGER = logging.getLogger(__name__)


class CompanyProvider(Protocol):
    @property
    def name(self) -> str:  # pragma: no cover - protocol definition
        ...

    async def fetch(self, session: aiohttp.ClientSession | None = None) -> list[Company]:
        ...


class CompanyDirectoryService:
    def __init__(
        self,
        providers: list[CompanyProvider],
        cache_path: Path,
        fallback_path: Path | None,
        ttl: timedelta,
        request_timeout: int = 15,
    ) -> None:
        self._providers = providers
        self._cache_path = cache_path
        self._fallback_path = fallback_path
        self._ttl = ttl
        self._request_timeout = request_timeout
        self._companies: list[Company] = []
        self._alias_map: dict[str, list[str]] = {}
        self._last_updated: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_all(self) -> list[Company]:
        if not self._companies:
            await self.refresh(force=False)
        return list(self._companies)

    async def get_alias_map(self) -> dict[str, list[str]]:
        await self.get_all()
        return {ticker: list(aliases) for ticker, aliases in self._alias_map.items()}

    async def search(self, query: str, exchange: str | None = None, limit: int = 10) -> list[Company]:
        await self.get_all()
        normalized_query = normalize_text(query)
        if not normalized_query:
            return []
        candidates = [
            company
            for company in self._companies
            if exchange is None or company.exchange == exchange
        ]
        direct: list[Company] = []
        for company in candidates:
            if normalized_query == normalize_text(company.ticker):
                return [company]
            if any(normalized_query in normalize_text(alias) for alias in company.aliases):
                direct.append(company)
        if direct:
            return direct[:limit]
        choices = {
            f"{company.exchange}:{company.ticker}": " ".join(company.aliases)
            for company in candidates
        }
        matches = process.extract(normalized_query, choices, limit=limit)
        result: list[Company] = []
        for key, score, _ in matches:
            if score <= 60:
                continue
            exchange_key, ticker = key.split(":", 1)
            found = await self.get(exchange_key, ticker)
            if found:
                result.append(found)
        return result

    async def get(self, exchange: str, ticker: str) -> Company | None:
        await self.get_all()
        for company in self._companies:
            if company.exchange == exchange and company.ticker.upper() == ticker.upper():
                return company
        return None

    async def refresh(self, force: bool = False) -> RefreshResult:
        async with self._lock:
            LOGGER.info("Refreshing company directory (force=%s)", force)
            cache = self._load_cache()
            if cache and not force and not self._is_stale(cache[0]):
                self._set_companies(cache[1], cache[0])
                LOGGER.info("Using cached company directory updated at %s", cache[0].isoformat())
                return RefreshResult(cache[1], cache[0], from_cache=True, used_fallback=False, errors=[])

            errors: list[str] = []
            companies: list[Company] = []
            timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                tasks = [self._fetch_provider(provider, session, errors) for provider in self._providers]
                results = await asyncio.gather(*tasks)
            provider_counts: dict[str, int] = {}
            for name, batch in results:
                provider_counts[name] = len(batch)
                companies.extend(batch)
            merged_preview = len(self._merge(companies)) if companies else 0
            LOGGER.info(
                "MOEX fetched: %s, SPB fetched: %s, merged: %s",
                provider_counts.get("MOEX", 0),
                provider_counts.get("SPB", 0),
                merged_preview,
            )

            if companies:
                merged = self._merge(companies)
                updated_at = datetime.now(timezone.utc)
                self._set_companies(merged, updated_at)
                self._save_cache(merged, updated_at)
                return RefreshResult(merged, updated_at, from_cache=False, used_fallback=False, errors=errors)

            if cache:
                self._set_companies(cache[1], cache[0])
                LOGGER.warning(
                    "Using cached company directory due to provider errors: %s", errors or "no data returned"
                )
                return RefreshResult(cache[1], cache[0], from_cache=True, used_fallback=False, errors=errors)

            fallback_companies = self._load_fallback()
            if fallback_companies:
                updated_at = datetime.now(timezone.utc)
                self._set_companies(fallback_companies, updated_at)
                LOGGER.warning(
                    "Using fallback company directory due to provider errors: %s",
                    errors or "no data returned",
                )
                return RefreshResult(
                    fallback_companies,
                    updated_at,
                    from_cache=False,
                    used_fallback=True,
                    errors=errors,
                )

            return RefreshResult([], None, from_cache=False, used_fallback=False, errors=errors)

    def stats(self) -> tuple[dict[str, int], datetime | None]:
        counts: dict[str, int] = {}
        for company in self._companies:
            counts[company.exchange] = counts.get(company.exchange, 0) + 1
        return counts, self._last_updated

    async def _fetch_provider(
        self,
        provider: CompanyProvider,
        session: aiohttp.ClientSession,
        errors: list[str],
    ) -> tuple[str, list[Company]]:
        try:
            return provider.name, await provider.fetch(session)
        except Exception as exc:  # noqa: BLE001
            message = f"{provider.name} fetch failed: {exc}"
            LOGGER.warning(message)
            errors.append(message)
            return provider.name, []

    def _is_stale(self, updated_at: datetime) -> bool:
        return datetime.now(timezone.utc) - updated_at > self._ttl

    def _set_companies(self, companies: list[Company], updated_at: datetime) -> None:
        self._companies = companies
        self._last_updated = updated_at
        alias_map: dict[str, list[str]] = {}
        for company in companies:
            aliases = list(company.aliases)
            if company.ticker not in aliases:
                aliases.append(company.ticker)
            ticker_upper = company.ticker.upper()
            alias_map[ticker_upper] = aliases
        self._alias_map = alias_map

    def _merge(self, companies: list[Company]) -> list[Company]:
        merged: dict[tuple[str, str], Company] = {}
        for company in companies:
            key = (company.exchange, company.ticker.upper())
            existing = merged.get(key)
            if not existing:
                merged[key] = company
                continue
            aliases = list({*existing.aliases, *company.aliases})
            merged[key] = Company(
                exchange=existing.exchange,
                ticker=existing.ticker,
                name=existing.name or company.name,
                isin=existing.isin or company.isin,
                type=existing.type or company.type,
                currency=existing.currency or company.currency,
                aliases=aliases,
                source=existing.source or company.source,
                updated_at=max(existing.updated_at, company.updated_at),
            )
        return list(merged.values())

    def _load_cache(self) -> tuple[datetime, list[Company]] | None:
        if not self._cache_path.exists():
            return None
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Failed to read cache: %s", exc)
            return None
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        updated_at_raw = meta.get("updated_at")
        companies_raw = data.get("companies") if isinstance(data, dict) else None
        if not updated_at_raw or not isinstance(companies_raw, list):
            return None
        try:
            updated_at = datetime.fromisoformat(updated_at_raw)
        except ValueError:
            return None
        companies = [self._deserialize_company(item) for item in companies_raw]
        companies = [company for company in companies if company is not None]
        return updated_at, companies

    def _save_cache(self, companies: list[Company], updated_at: datetime) -> None:
        payload = {
            "meta": {"updated_at": updated_at.isoformat()},
            "companies": [self._serialize_company(company) for company in companies],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_fallback(self) -> list[Company]:
        if not self._fallback_path or not self._fallback_path.exists():
            return []
        try:
            data = json.loads(self._fallback_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Failed to read fallback: %s", exc)
            return []
        if isinstance(data, dict) and "companies" in data:
            return [
                company
                for company in (self._deserialize_company(item) for item in data.get("companies", []))
                if company is not None
            ]
        if isinstance(data, dict):
            return self._deserialize_legacy_fallback(data)
        return []

    def _deserialize_legacy_fallback(self, data: dict[str, list[str]]) -> list[Company]:
        now = datetime.now(timezone.utc)
        companies: list[Company] = []
        for ticker, aliases in data.items():
            if not ticker:
                continue
            name = aliases[0] if aliases else ticker
            companies.append(
                Company(
                    exchange="MOEX",
                    ticker=ticker,
                    name=name,
                    isin=None,
                    type=None,
                    currency=None,
                    aliases=aliases,
                    source={"provider": "fallback", "url": str(self._fallback_path)},
                    updated_at=now,
                )
            )
        return companies

    def _serialize_company(self, company: Company) -> dict[str, object]:
        payload = asdict(company)
        payload["updated_at"] = company.updated_at.isoformat()
        return payload

    def _deserialize_company(self, payload: object) -> Company | None:
        if not isinstance(payload, dict):
            return None
        try:
            updated_at = datetime.fromisoformat(str(payload.get("updated_at")))
        except (TypeError, ValueError):
            updated_at = datetime.now(timezone.utc)
        return Company(
            exchange=str(payload.get("exchange")),
            ticker=str(payload.get("ticker")),
            name=str(payload.get("name")),
            isin=payload.get("isin"),
            type=payload.get("type"),
            currency=payload.get("currency"),
            aliases=list(payload.get("aliases") or []),
            source=dict(payload.get("source") or {}),
            updated_at=updated_at,
        )


def build_company_directory(settings) -> CompanyDirectoryService:
    from app.companies.providers.moex import MoexProvider
    from app.companies.providers.spb import SpbProvider

    cache_path = Path(settings.companies_cache_path)
    fallback_path = Path(settings.companies_fallback_path) if settings.companies_fallback_path else None
    providers = [
        MoexProvider(settings.moex_iss_base_url),
        SpbProvider(settings.alor_base_url),
    ]
    return CompanyDirectoryService(
        providers=providers,
        cache_path=cache_path,
        fallback_path=fallback_path,
        ttl=timedelta(hours=settings.companies_refresh_ttl_hours),
        request_timeout=settings.request_timeout,
    )
