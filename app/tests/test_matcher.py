from datetime import datetime, timezone

from app.news.directory import Company
from app.news.matcher import CompanyMatcher


def test_matcher_finds_company() -> None:
    now = datetime.now(timezone.utc)
    companies = [
        Company(
            exchange="MOEX",
            ticker="LKOH",
            name="Лукойл",
            isin=None,
            type="share",
            currency="RUB",
            aliases=["Лукойл", "LKOH"],
            source={"provider": "test"},
            updated_at=now,
        ),
        Company(
            exchange="MOEX",
            ticker="SBER",
            name="Сбербанк",
            isin=None,
            type="share",
            currency="RUB",
            aliases=["Сбербанк", "SBER"],
            source={"provider": "test"},
            updated_at=now,
        ),
    ]
    matcher = CompanyMatcher(companies)

    matches = matcher.match("Лукойл объявил дивиденды", "Акции LKOH выросли")
    assert "LKOH" in matches
    assert matches["LKOH"] >= 3
