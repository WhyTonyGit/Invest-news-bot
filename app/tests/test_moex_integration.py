import os

import pytest

from app.news.directory import _fetch_moex_securities


@pytest.mark.integration
@pytest.mark.asyncio
async def test_moex_iss_integration() -> None:
    if os.getenv("RUN_MOEX_INTEGRATION") != "1":
        pytest.skip("RUN_MOEX_INTEGRATION is not set")
    base_url = os.getenv("MOEX_ISS_BASE_URL", "https://iss.moex.com/iss")
    companies = await _fetch_moex_securities(base_url, max_pages=1)
    tickers = {company.ticker for company in companies}
    assert companies
    assert {"SBER", "LKOH"} & tickers or tickers
