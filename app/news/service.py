from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.news.dedupe import canonical_hash, is_similar
from app.news.matcher import CompanyMatcher
from app.news.parser import ParsedItem


@dataclass(frozen=True)
class NewsCandidate:
    title: str
    summary: str | None
    url: str
    published_at: datetime
    source_name: str
    source_id: int
    mentions: dict[str, int]
    canonical_hash: str
    category: str


@dataclass(frozen=True)
class NewsCluster:
    category: str
    items: list[NewsCandidate]


class NewsService:
    def __init__(self, matcher: CompanyMatcher) -> None:
        self.matcher = matcher
        self._recent_titles: list[str] = []

    def prepare_candidates(
        self,
        items: Iterable[ParsedItem],
        source_name: str,
        source_id: int,
        last_item_ts: datetime | None,
        require_mentions: bool,
    ) -> list[NewsCandidate]:
        prepared: list[NewsCandidate] = []
        for item in items:
            if last_item_ts and item.published <= last_item_ts:
                continue
            mentions = self.matcher.match(item.title, item.summary)
            if require_mentions and not mentions:
                continue
            if self._is_recent_duplicate(item.title):
                continue
            prepared.append(
                NewsCandidate(
                    title=item.title,
                    summary=item.summary,
                    url=item.link,
                    published_at=item.published,
                    source_name=source_name,
                    source_id=source_id,
                    mentions=mentions,
                    canonical_hash=canonical_hash(item.title, item.summary, item.link),
                    category=categorize(item.title, item.summary),
                )
            )
        return prepared

    def cluster(self, items: list[NewsCandidate]) -> list[NewsCluster]:
        clusters: list[list[NewsCandidate]] = []
        for item in items:
            placed = False
            for cluster in clusters:
                if is_similar(item.title, cluster[0].title, threshold=90):
                    cluster.append(item)
                    placed = True
                    break
            if not placed:
                clusters.append([item])
        return [NewsCluster(category=cluster[0].category, items=cluster) for cluster in clusters]

    def _is_recent_duplicate(self, title: str) -> bool:
        for existing in self._recent_titles:
            if is_similar(title, existing, threshold=90):
                return True
        self._recent_titles.append(title)
        if len(self._recent_titles) > 200:
            self._recent_titles = self._recent_titles[-100:]
        return False


def categorize(title: str, summary: str | None) -> str:
    text = f"{title} {summary or ''}".lower()
    if any(word in text for word in ["дивиденд", "дивиденды", "дивиденда"]):
        return "DIVIDENDS"
    if any(word in text for word in ["отчет", "отчетность", "мсфо", "рсбу", "earnings"]):
        return "EARNINGS"
    if any(word in text for word in ["слияние", "поглощение", "m&a", "acquisition"]):
        return "M&A"
    if any(word in text for word in ["ставка", "инфляц", "макро", "cpi", "gdp"]):
        return "MACRO"
    if any(word in text for word in ["регулятор", "санкц", "закон", "правил"]):
        return "REGULATION"
    return "OTHER"


def impact_score(category: str) -> int:
    return {
        "EARNINGS": 5,
        "DIVIDENDS": 4,
        "M&A": 4,
        "MACRO": 3,
        "REGULATION": 3,
        "OTHER": 2,
    }.get(category, 2)
