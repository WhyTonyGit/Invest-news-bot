import os

import pytest

from app.config import load_settings


def test_telegram_bot_token_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "primary")
    monkeypatch.setenv("BOT_TOKEN", "fallback")
    settings = load_settings()
    assert settings.bot_token == "primary"


def test_bot_token_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "fallback")
    settings = load_settings()
    assert settings.bot_token == "fallback"
