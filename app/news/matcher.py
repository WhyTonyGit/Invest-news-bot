from __future__ import annotations

from dataclasses import dataclass
from app.news.directory import Company
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
    def __init__(self, companies: list[Company]) -> None:
        self._companies = companies

    def update(self, companies: list[Company]) -> None:
        self._companies = companies

    def match(self, title: str, summary: str | None) -> dict[str, int]:
        results: dict[str, int] = {}
        title_norm = normalize_text(title)
        summary_norm = normalize_text(summary or "")

        for record in self._companies:
            aliases = record.aliases
            title_match = contains_alias(title, aliases)
            summary_match = contains_alias(summary or "", aliases) if summary else False

            if not title_match and not summary_match:
                continue

            score = (2 if title_match else 0) + (1 if summary_match else 0)
            if any(keyword in title_norm or keyword in summary_norm for keyword in CONTEXT_KEYWORDS):
                score += 1

            if record.ticker in NOISY_TICKERS or len(record.ticker) <= 4:
                if not any(keyword in title_norm or keyword in summary_norm for keyword in CONTEXT_KEYWORDS):
                    if not contains_alias(title, [record.ticker, f"${record.ticker}"]):
                        continue

            results[record.ticker] = score

        return results
