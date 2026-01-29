from pathlib import Path

from app.news.matcher import CompanyMatcher


def test_matcher_finds_company(tmp_path: Path) -> None:
    companies_path = tmp_path / "companies.json"
    companies_path.write_text(
        """
        [
          {
            "exchange": "MOEX",
            "ticker": "LKOH",
            "name": "Лукойл",
            "isin": null,
            "type": "share",
            "currency": "RUB",
            "aliases": ["Лукойл", "LKOH"],
            "source": {"provider": "test", "url": null, "asof_date": null},
            "updated_at": "2024-01-01T00:00:00Z"
          },
          {
            "exchange": "MOEX",
            "ticker": "SBER",
            "name": "Сбербанк",
            "isin": null,
            "type": "share",
            "currency": "RUB",
            "aliases": ["Сбербанк", "SBER"],
            "source": {"provider": "test", "url": null, "asof_date": null},
            "updated_at": "2024-01-01T00:00:00Z"
          }
        ]
        """,
        encoding="utf-8",
    )
    matcher = CompanyMatcher(companies_path)

    matches = matcher.match("Лукойл объявил дивиденды", "Акции LKOH выросли")
    assert "LKOH" in matches
    assert matches["LKOH"] >= 3
