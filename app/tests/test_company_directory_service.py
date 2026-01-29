from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.companies.models import Company
from app.companies.service import CompanyDirectoryService


class FakeProvider:
    def __init__(self, name: str, companies: list[Company] | None = None, exc: Exception | None = None) -> None:
        self._name = name
        self._companies = companies or []
        self._exc = exc
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def fetch(self, session) -> list[Company]:
        self.calls += 1
        if self._exc:
            raise self._exc
        return list(self._companies)


def make_company(ticker: str, aliases: list[str]) -> Company:
    return Company(
        exchange="MOEX",
        ticker=ticker,
        name=aliases[0] if aliases else ticker,
        isin=None,
        type=None,
        currency=None,
        aliases=aliases,
        source={"provider": "test"},
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_refresh_merge_dedup(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    provider_a = FakeProvider("A", [make_company("SBER", ["Сбер"])])
    provider_b = FakeProvider("B", [make_company("SBER", ["Сбербанк"])])
    service = CompanyDirectoryService(
        providers=[provider_a, provider_b],
        cache_path=cache_path,
        fallback_path=None,
        ttl=timedelta(hours=24),
    )

    result = await service.refresh(force=True)

    assert len(result.companies) == 1
    merged_aliases = result.companies[0].aliases
    assert "Сбер" in merged_aliases
    assert "Сбербанк" in merged_aliases


@pytest.mark.asyncio
async def test_refresh_respects_ttl(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    provider = FakeProvider("A", [make_company("SBER", ["Сбер"])])
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        fallback_path=None,
        ttl=timedelta(hours=24),
    )
    now = datetime.now(timezone.utc)
    service._save_cache([make_company("SBER", ["Сбер"])], now)

    result = await service.refresh(force=False)

    assert result.from_cache is True
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_refresh_fallback_to_cache_on_error(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    provider = FakeProvider("A", exc=RuntimeError("boom"))
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        fallback_path=None,
        ttl=timedelta(hours=0),
    )
    cached_company = make_company("GAZP", ["Газпром"])
    service._save_cache([cached_company], datetime.now(timezone.utc))

    result = await service.refresh(force=True)

    assert result.from_cache is True
    assert result.companies[0].ticker == "GAZP"


@pytest.mark.asyncio
async def test_refresh_fallback_to_bundled_file(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    fallback_path = tmp_path / "fallback.json"
    fallback_path.write_text('{"SBER": ["Сбербанк", "SBER"]}', encoding="utf-8")
    provider = FakeProvider("A", exc=RuntimeError("boom"))
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        fallback_path=fallback_path,
        ttl=timedelta(hours=0),
    )

    result = await service.refresh(force=True)

    assert result.used_fallback is True
    assert result.companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_search_contract(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    provider = FakeProvider("A", [make_company("SBER", ["Сбербанк", "SBER"])])
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        fallback_path=None,
        ttl=timedelta(hours=24),
    )
    await service.refresh(force=True)

    results = await service.search("сбер")

    assert results
    assert results[0].ticker == "SBER"
