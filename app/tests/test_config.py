import os

import pytest

from app.config import load_settings


def test_uses_telegram_bot_token_if_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    settings = load_settings()
    assert settings.bot_token == "dummy"


def test_falls_back_to_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "dummy")
    settings = load_settings()
    assert settings.bot_token == "dummy"


def test_raises_if_both_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        load_settings()
    message = str(excinfo.value)
    assert "TELEGRAM_BOT_TOKEN" in message
    assert "BOT_TOKEN" in message
