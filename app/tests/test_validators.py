import pytest

from app.bot.validators import validate_interval, validate_limit


def test_validate_interval_success() -> None:
    assert validate_interval("30") == 30
    assert validate_interval("120") == 120


def test_validate_interval_invalid() -> None:
    assert validate_interval("29") is None
    assert validate_interval("121") is None
    assert validate_interval("abc") is None


def test_validate_limit_success() -> None:
    assert validate_limit("1") == 1
    assert validate_limit("1000") == 1000


def test_validate_limit_invalid() -> None:
    assert validate_limit("0") is None
    assert validate_limit("1001") is None
    assert validate_limit("abc") is None
