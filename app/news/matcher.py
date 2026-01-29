from __future__ import annotations

from dataclasses import dataclass

from app.companies.service import CompanyDirectoryService
from app.utils.normalize import contains_alias, normalize_text

CONTEXT_KEYWORDS = {
    "акции",
    "бумаги",
    "компания",
    "дивиденды",
    "отчет",
    "отчетность",
    "мосбиржа",
    "биржа",
    "рынок",
    "ipo",
    "облигации",
    "выручка",
}

NOISY_TICKERS = {"MTSS", "MVID", "YNDX", "VKCO"}


@dataclass(frozen=True)
class MatchResult:
    ticker: str
    score: int


class CompanyMatcher:
    def __init__(self, directory: CompanyDirectoryService) -> None:
        self.directory = directory

    async def match(self, title: str, summary: str | None) -> dict[str, int]:
        companies = await self.directory.get_alias_map()
        results: dict[str, int] = {}
        title_norm = normalize_text(title)
        summary_norm = normalize_text(summary or "")

        for ticker, aliases in companies.items():
            alias_list = list(aliases)
            if ticker not in alias_list:
                alias_list.append(ticker)
            alias_list.append(f"${ticker}")
            title_match = contains_alias(title, alias_list)
            summary_match = contains_alias(summary or "", alias_list) if summary else False

            if not title_match and not summary_match:
                continue

            score = (2 if title_match else 0) + (1 if summary_match else 0)
            if any(keyword in title_norm or keyword in summary_norm for keyword in CONTEXT_KEYWORDS):
                score += 1

            if ticker in NOISY_TICKERS or len(ticker) <= 4:
                if not any(keyword in title_norm or keyword in summary_norm for keyword in CONTEXT_KEYWORDS):
                    if not contains_alias(title, [ticker, f"${ticker}"]):
                        continue

            results[ticker] = score

        return results
