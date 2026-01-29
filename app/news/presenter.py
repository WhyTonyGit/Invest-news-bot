from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRef:
    name: str
    url: str


def format_sources(sources: list[SourceRef], limit: int = 5) -> str:
    if not sources:
        return "—"
    lines = [f"• <a href=\"{source.url}\">{source.name}</a>" for source in sources[:limit]]
    return "\n".join(lines) if lines else "—"


def build_news_message(
    title: str,
    summary_line: str,
    companies: str,
    category: str,
    impact: int,
    sources: list[SourceRef],
    published: str,
) -> str:
    sources_lines = format_sources(sources)
    return (
        f"<b>{title}</b>\n"
        f"{summary_line}\n"
        f"Компании: {companies}\n"
        f"Категория: {category} · Impact: {impact}\n"
        f"Источники:\n{sources_lines}\n"
        f"Время: {published}"
    )
