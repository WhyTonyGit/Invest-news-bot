from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    url: str


DEFAULT_SOURCES: list[Source] = [
    Source(name="РБК Новости", url="https://rssexport.rbc.ru/rbcnews/news/30/full.rss"),
    Source(name="РБК Финансы", url="https://rssexport.rbc.ru/rbcnews/news/finance/full.rss"),
    Source(name="Интерфакс Финансы", url="https://www.interfax.ru/rss.asp?sec=153"),
    Source(name="Интерфакс Рынки", url="https://www.interfax.ru/rss.asp?sec=154"),
    Source(name="РИА Новости Экономика", url="https://ria.ru/export/rss2/economy/index.xml"),
    Source(name="РИА Новости Рынки", url="https://ria.ru/export/rss2/markets/index.xml"),
    Source(name="Коммерсантъ Экономика", url="https://www.kommersant.ru/RSS/section-economics.xml"),
    Source(name="Коммерсантъ Финансы", url="https://www.kommersant.ru/RSS/section-finances.xml"),
    Source(name="Ведомости", url="https://www.vedomosti.ru/rss/rubric/finance"),
    Source(name="ТАСС Экономика", url="https://tass.ru/rss/v2.xml?sections=ekonomika"),
]
