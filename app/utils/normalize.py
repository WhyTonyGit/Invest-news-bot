from __future__ import annotations

import re
from typing import Iterable

RE_MULTISPACE = re.compile(r"\s+")
RE_PUNCT = re.compile(r"[^0-9a-zA-Zа-яА-ЯёЁ$# ]+")


def normalize_text(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    cleaned = RE_PUNCT.sub(" ", lowered)
    return RE_MULTISPACE.sub(" ", cleaned).strip()


def contains_alias(text: str, aliases: Iterable[str]) -> bool:
    normalized = f" {normalize_text(text)} "
    for alias in aliases:
        alias_norm = normalize_text(alias)
        if not alias_norm:
            continue
        if f" {alias_norm} " in normalized:
            return True
    return False
