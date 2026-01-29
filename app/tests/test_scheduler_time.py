from datetime import datetime, timezone

from app.news.time_utils import normalize_ts


def test_scheduler_timestamp_compare_naive_vs_aware() -> None:
    naive = datetime(2024, 1, 1, 12, 0, 0)
    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    assert normalize_ts(naive) <= normalize_ts(aware)


def test_scheduler_timestamp_compare_both_naive() -> None:
    first = datetime(2024, 1, 1, 12, 0, 0)
    second = datetime(2024, 1, 1, 12, 1, 0)

    assert normalize_ts(first) < normalize_ts(second)
