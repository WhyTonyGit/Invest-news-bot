import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.news.directory import Company, CompanyDirectoryService, RefreshResult


class FakeProvider:
    def __init__(self, companies: list[Company], should_fail: bool = False) -> None:
        self.companies = companies
        self.calls = 0
        self.should_fail = should_fail

    async def fetch(self) -> list[Company]:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("provider error")
        return self.companies


@pytest.mark.asyncio
async def test_refresh_uses_cache_ttl(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    cache_path = tmp_path / "companies_cache.json"
    cache_payload = {
        "updated_at": now.isoformat(),
        "companies": [
            {
                "exchange": "MOEX",
                "ticker": "SBER",
                "name": "Сбербанк",
                "isin": None,
                "type": "share",
                "currency": "RUB",
                "aliases": ["SBER"],
                "source": {"provider": "cache"},
                "updated_at": now.isoformat(),
            }
        ],
    }
    cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")
    provider = FakeProvider([])
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        ttl_hours=24,
        fallback_path=tmp_path / "fallback.json",
    )
    await service.startup()
    result = await service.refresh(force=False)
    assert result.updated is False
    assert provider.calls == 0
    companies = await service.get_all()
    assert companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_refresh_fallback_on_error(tmp_path: Path) -> None:
    fallback_path = tmp_path / "fallback.json"
    fallback_payload = {"SBER": ["Сбербанк", "SBER"]}
    fallback_path.write_text(json.dumps(fallback_payload), encoding="utf-8")
    provider = FakeProvider([], should_fail=True)
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=24,
        fallback_path=fallback_path,
    )
    result = await service.refresh(force=True)
    assert isinstance(result, RefreshResult)
    companies = await service.get_all()
    assert companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_refresh_partial_success(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    ok_provider = FakeProvider(
        [
            Company(
                exchange="MOEX",
                ticker="SBER",
                name="Сбербанк",
                isin=None,
                type="share",
                currency="RUB",
                aliases=["SBER"],
                source={"provider": "ok"},
                updated_at=now,
            )
        ]
    )
    failing_provider = FakeProvider([], should_fail=True)
    service = CompanyDirectoryService(
        providers=[ok_provider, failing_provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=24,
        fallback_path=tmp_path / "fallback.json",
    )
    result = await service.refresh(force=True)
    assert result.updated is True
    assert result.count == 1
    companies = await service.get_all()
    assert companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_refresh_uses_cache_when_providers_fail(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    cache_path = tmp_path / "companies_cache.json"
    cache_payload = {
        "updated_at": now.isoformat(),
        "companies": [
            {
                "exchange": "MOEX",
                "ticker": "SBER",
                "name": "Сбербанк",
                "isin": None,
                "type": "share",
                "currency": "RUB",
                "aliases": ["SBER"],
                "source": {"provider": "cache"},
                "updated_at": now.isoformat(),
            }
        ],
    }
    cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")
    failing_provider = FakeProvider([], should_fail=True)
    service = CompanyDirectoryService(
        providers=[failing_provider],
        cache_path=cache_path,
        ttl_hours=0,
        fallback_path=tmp_path / "fallback.json",
    )
    await service.startup()
    result = await service.refresh(force=True)
    assert result.updated is False
    companies = await service.get_all()
    assert companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_refresh_no_data_no_fallback(tmp_path: Path) -> None:
    failing_provider = FakeProvider([], should_fail=True)
    service = CompanyDirectoryService(
        providers=[failing_provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=0,
        fallback_path=tmp_path / "fallback.json",
    )
    result = await service.refresh(force=True)
    assert result.updated is False
    companies = await service.get_all()
    assert companies == []


@pytest.mark.asyncio
async def test_refresh_uses_fallback_when_provider_returns_empty(tmp_path: Path) -> None:
    fallback_path = tmp_path / "fallback.json"
    fallback_payload = {"SBER": ["Сбербанк", "SBER"]}
    fallback_path.write_text(json.dumps(fallback_payload), encoding="utf-8")
    provider = FakeProvider([])
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=0,
        fallback_path=fallback_path,
    )
    result = await service.refresh(force=True)
    assert result.updated is False
    companies = await service.get_all()
    assert companies[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_refresh_ttl_expired_triggers_provider(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    cache_path = tmp_path / "companies_cache.json"
    cache_payload = {
        "updated_at": now.isoformat(),
        "companies": [],
    }
    cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")
    provider = FakeProvider([])
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=cache_path,
        ttl_hours=0,
        fallback_path=tmp_path / "fallback.json",
    )
    await service.startup()
    await service.refresh(force=False)
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_search_matches_aliases(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    provider = FakeProvider(
        [
            Company(
                exchange="MOEX",
                ticker="SBER",
                name="Сбербанк",
                isin=None,
                type="share",
                currency="RUB",
                aliases=["Сбербанк", "SBER", "Сбер"],
                source={"provider": "test"},
                updated_at=now,
            )
        ]
    )
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=0,
        fallback_path=tmp_path / "fallback.json",
    )
    await service.refresh(force=True)
    results = await service.search("сбер")
    assert results[0].ticker == "SBER"


@pytest.mark.asyncio
async def test_directory_search_finds_known(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    provider = FakeProvider(
        [
            Company(
                exchange="MOEX",
                ticker="SBER",
                name="Сбербанк",
                isin=None,
                type="share",
                currency="RUB",
                aliases=["Сбербанк", "SBER", "Сбер"],
                source={"provider": "test"},
                updated_at=now,
            )
        ]
    )
    service = CompanyDirectoryService(
        providers=[provider],
        cache_path=tmp_path / "companies_cache.json",
        ttl_hours=0,
        fallback_path=tmp_path / "fallback.json",
    )
    await service.refresh(force=True)
    results_ticker = await service.search("SBER")
    results_name = await service.search("сбер")
    assert results_ticker[0].ticker == "SBER"
    assert results_name[0].ticker == "SBER"
