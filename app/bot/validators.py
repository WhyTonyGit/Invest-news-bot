from __future__ import annotations


def validate_interval(value: str) -> int | None:
    value = value.strip()
    if not value.isdigit():
        return None
    interval = int(value)
    if 30 <= interval <= 120:
        return interval
    return None


def validate_limit(value: str, max_limit: int = 1000) -> int | None:
    value = value.strip()
    if not value.isdigit():
        return None
    limit = int(value)
    if 1 <= limit <= max_limit:
        return limit
    return None
