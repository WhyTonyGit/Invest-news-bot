import pytest

aioresponses = pytest.importorskip("aioresponses").aioresponses

from app.news.directory import AlorSPBProvider, MOEXProvider


@pytest.mark.asyncio
async def test_moex_provider_parses_and_paginates() -> None:
    base_url = "https://iss.moex.com/iss"
    url = f"{base_url}/engines/stock/markets/shares/securities.json"
    payload_page_1 = {
        "securities": {
            "columns": ["SECID", "SHORTNAME", "NAME", "ISIN", "SECNAME", "CURRENCY", "FACEUNIT"],
            "data": [["SBER", "Сбер", "Сбербанк", "RU0009029540", "Акции", "RUB", None]],
        }
    }
    payload_page_2 = {"securities": {"columns": ["SECID"], "data": []}}
    with aioresponses() as mocked:
        mocked.get(url, payload=payload_page_1, params={"iss.meta": "off", "iss.only": "securities",
                                                      "securities.columns": "SECID,SHORTNAME,NAME,ISIN,SECNAME,CURRENCY,FACEUNIT",
                                                      "start": "0"})
        mocked.get(url, payload=payload_page_2, params={"iss.meta": "off", "iss.only": "securities",
                                                      "securities.columns": "SECID,SHORTNAME,NAME,ISIN,SECNAME,CURRENCY,FACEUNIT",
                                                      "start": "1"})
        provider = MOEXProvider(base_url)
        companies = await provider.fetch()
    assert len(companies) == 1
    assert companies[0].ticker == "SBER"
    assert companies[0].exchange == "MOEX"
    assert companies[0].updated_at.tzinfo is not None


@pytest.mark.asyncio
async def test_alor_provider_filters_spb() -> None:
    base_url = "https://api.alor.ru"
    url = f"{base_url}/md/v2/Securities"
    payload = [
        {"symbol": "SBER", "shortName": "Sber", "exchange": "SPBX"},
        {"symbol": "GAZP", "shortName": "Gazprom", "exchange": "MOEX"},
    ]
    with aioresponses() as mocked:
        mocked.get(url, payload=payload)
        provider = AlorSPBProvider(base_url)
        companies = await provider.fetch()
    assert len(companies) == 1
    assert companies[0].ticker == "SBER"
    assert companies[0].exchange == "SPB"
    assert companies[0].updated_at.tzinfo is not None
