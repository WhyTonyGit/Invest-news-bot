from __future__ import annotations

import hashlib

from rapidfuzz import fuzz

from app.utils.normalize import normalize_text


def canonical_hash(title: str, summary: str | None, url: str | None = None) -> str:
    base = normalize_text(title)
    if summary:
        base = f"{base} {normalize_text(summary)}"
    if url:
        base = f"{base} {url}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return digest


def is_similar(title_a: str, title_b: str, threshold: int = 90) -> bool:
    return fuzz.token_set_ratio(title_a, title_b) >= threshold
