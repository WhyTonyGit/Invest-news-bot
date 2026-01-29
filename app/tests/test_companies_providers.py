import pytest

from app.companies.providers.moex import MoexProvider
from app.companies.providers.spb import SpbProvider


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.status = 200

    async def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSession:
    def __init__(self, payloads: dict[int | None, object]) -> None:
        self._payloads = payloads

    def get(self, url: str, params: dict | None = None):
        start = params.get("start") if params else None
        payload = self._payloads.get(start)
        return FakeResponse(payload)


def test_moex_provider_uses_trust_env_and_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummySession:
        def __init__(self, *args, **kwargs) -> None:
            captured["timeout"] = kwargs.get("timeout")
            captured["trust_env"] = kwargs.get("trust_env")

        async def close(self) -> None:
            return None

    monkeypatch.setattr("app.companies.providers.moex.aiohttp.ClientSession", DummySession)
    provider = MoexProvider(base_url="https://iss.moex.com/iss")
    session = provider._create_session()

    assert captured["trust_env"] is True
    timeout = captured["timeout"]
    assert timeout.total == 15
    assert timeout.connect == 5
    assert timeout.sock_read == 10
    assert session is not None


@pytest.mark.asyncio
async def test_moex_provider_pagination() -> None:
    provider = MoexProvider(base_url="https://iss.moex.com/iss", page_size=2)

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

    session = FakeSession({0: payload_page_1, 2: payload_page_2})
    companies = await provider.fetch(session)

    tickers = {company.ticker for company in companies}
    assert tickers == {"SBER", "GAZP", "LKOH"}
    sber = next(company for company in companies if company.ticker == "SBER")
    assert "Сбер" in sber.aliases
    assert "сбербанк" in [alias.lower() for alias in sber.aliases]


@pytest.mark.asyncio
async def test_spb_provider_filters_exchange() -> None:
    provider = SpbProvider(base_url="https://api.alor.ru")
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

    session = FakeSession({None: payload})
    companies = await provider.fetch(session)

    tickers = {company.ticker for company in companies}
    assert tickers == {"AAPL", "TCSG"}
