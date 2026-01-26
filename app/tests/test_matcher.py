from pathlib import Path

from app.news.matcher import CompanyMatcher


def test_matcher_finds_company(tmp_path: Path) -> None:
    companies_path = tmp_path / "companies.json"
    companies_path.write_text(
        "{\"LKOH\": [\"Лукойл\", \"LKOH\"], \"SBER\": [\"Сбербанк\", \"SBER\"]}",
        encoding="utf-8",
    )
    matcher = CompanyMatcher(companies_path)

    matches = matcher.match("Лукойл объявил дивиденды", "Акции LKOH выросли")
    assert "LKOH" in matches
    assert matches["LKOH"] >= 3
