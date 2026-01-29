from datetime import datetime, timezone

from app.bot.handlers import _find_candidates
from app.news.directory import Company


def test_find_candidates_matches_ticker_and_alias() -> None:
    now = datetime.now(timezone.utc)
    companies = [
        Company(
            exchange="MOEX",
            ticker="SBER",
            name="Сбербанк",
            isin=None,
            type="share",
            currency="RUB",
            aliases=["Сбер", "SBER"],
            source={"provider": "test"},
            updated_at=now,
        ),
        Company(
            exchange="MOEX",
            ticker="GAZP",
            name="Газпром",
            isin=None,
            type="share",
            currency="RUB",
            aliases=["Газпром", "GAZP"],
            source={"provider": "test"},
            updated_at=now,
        ),
    ]
    assert _find_candidates("SBER", companies)[0].ticker == "SBER"
    assert _find_candidates("сбер", companies)[0].ticker == "SBER"
    assert _find_candidates("Газпром", companies)[0].ticker == "GAZP"
