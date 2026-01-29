import pytest

from app.news.matcher import CompanyMatcher


class FakeDirectory:
    async def get_alias_map(self) -> dict[str, list[str]]:
        return {"LKOH": ["Лукойл", "LKOH"], "SBER": ["Сбербанк", "SBER"]}


@pytest.mark.asyncio
async def test_matcher_finds_company() -> None:
    matcher = CompanyMatcher(FakeDirectory())

    matches = await matcher.match("Лукойл объявил дивиденды", "Акции LKOH выросли")
    assert "LKOH" in matches
    assert matches["LKOH"] >= 3
