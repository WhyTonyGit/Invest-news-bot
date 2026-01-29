import os

import aiohttp
import pytest

from app.companies.providers.moex import MoexProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_moex_integration() -> None:
    if os.getenv("RUN_MOEX_INTEGRATION") != "1":
        pytest.skip("RUN_MOEX_INTEGRATION not set")
    provider = MoexProvider(base_url="https://iss.moex.com/iss", page_size=20)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        companies = await provider.fetch(session)

    assert companies
    assert any(company.ticker == "SBER" for company in companies)
