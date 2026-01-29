import re

import aiohttp
import pytest
from aioresponses import aioresponses

from app.companies.providers.moex import MoexProvider
from app.companies.providers.spb import SpbProvider


@pytest.mark.asyncio
async def test_moex_provider_pagination() -> None:
    provider = MoexProvider(base_url="https://iss.moex.com/iss", page_size=2)
    url = provider._build_url()

    payload_page_1 = {
        "securities": {
            "columns": ["SECID", "SHORTNAME", "NAME", "ISIN"],
            "data": [
                ["SBER", "Сбер", "ПАО Сбербанк", "RU0009029540"],
                ["GAZP", "Газпром", "ПАО Газпром", "RU0007661625"],
            ],
        }
    }
    payload_page_2 = {
        "securities": {
            "columns": ["SECID", "SHORTNAME", "NAME", "ISIN"],
            "data": [["LKOH", "Лукойл", "ПАО Лукойл", None]],
        }
    }

    with aioresponses() as mocked:
        mocked.get(re.compile(rf"{re.escape(url)}.*start=0.*"), payload=payload_page_1)
        mocked.get(re.compile(rf"{re.escape(url)}.*start=2.*"), payload=payload_page_2)
        async with aiohttp.ClientSession() as session:
            companies = await provider.fetch(session)

    tickers = {company.ticker for company in companies}
    assert tickers == {"SBER", "GAZP", "LKOH"}
    sber = next(company for company in companies if company.ticker == "SBER")
    assert "Сбер" in sber.aliases
    assert "сбербанк" in [alias.lower() for alias in sber.aliases]


@pytest.mark.asyncio
async def test_spb_provider_filters_exchange() -> None:
    provider = SpbProvider(base_url="https://api.alor.ru")
    url = provider._build_url()
    payload = [
        {
            "symbol": "AAPL",
            "exchange": "SPBX",
            "name": "Apple Inc",
            "isin": "US0378331005",
        },
        {"symbol": "MSFT", "exchange": "NASDAQ", "name": "Microsoft"},
        {"symbol": "TCSG", "board": "SPB", "name": "TCS Group"},
        {"symbol": "UNKNOWN", "name": "Missing exchange"},
    ]

    with aioresponses() as mocked:
        mocked.get(url, payload=payload)
        async with aiohttp.ClientSession() as session:
            companies = await provider.fetch(session)

    tickers = {company.ticker for company in companies}
    assert tickers == {"AAPL", "TCSG"}
