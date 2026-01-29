from __future__ import annotations

import re

from app.utils.normalize import normalize_text

RE_LEGAL_FORM = re.compile(
    r"^(публичное акционерное общество|пао|оао|ао|ооо|zao|pjsc|ojsc)\s+",
    re.IGNORECASE,
)


def strip_legal_form(name: str) -> str:
    cleaned = name.replace("«", " ").replace("»", " ").replace("\"", " ")
    cleaned = RE_LEGAL_FORM.sub("", cleaned.strip())
    return " ".join(cleaned.split())


def build_aliases(ticker: str, name: str | None) -> list[str]:
    aliases: list[str] = []
    if ticker:
        aliases.append(ticker)
    if name:
        aliases.append(name)
        aliases.append(name.lower())
        stripped = strip_legal_form(name)
        if stripped and stripped.lower() not in {name.lower()}:
            aliases.append(stripped)
    normalized = [normalize_text(alias) for alias in aliases if alias]
    for alias in normalized:
        if alias and alias not in aliases:
            aliases.append(alias)
    deduped: list[str] = []
    seen = set()
    for alias in aliases:
        if alias and alias not in seen:
            deduped.append(alias)
            seen.add(alias)
    return deduped
