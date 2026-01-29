from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_settings
from app.main import run_app


class DummyDirectory:
    def __init__(self) -> None:
        self.refresh = AsyncMock()

    async def get_alias_map(self) -> dict[str, list[str]]:
        return {}


@pytest.mark.asyncio
async def test_startup_refresh_called_before_polling(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    settings = load_settings()

    dispatcher = Dispatcher(storage=MemoryStorage())
    refresh_called = {"value": False}

    async def refresh_side_effect(*, force: bool) -> None:
        refresh_called["value"] = True

    async def start_polling_side_effect(*args, **kwargs) -> None:
        assert refresh_called["value"] is True

    directory = DummyDirectory()
    directory.refresh.side_effect = refresh_side_effect
    dispatcher.start_polling = AsyncMock(side_effect=start_polling_side_effect)

    fake_bot = SimpleNamespace()

    await run_app(settings, bot=fake_bot, dispatcher=dispatcher, company_directory=directory)

    directory.refresh.assert_awaited_once_with(force=True)
