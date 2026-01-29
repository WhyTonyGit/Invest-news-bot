from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from app.bot.handlers import add_company


class DummySessionmaker:
    def __call__(self):
        return self

    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):
        return None


def make_settings():
    return SimpleNamespace(
        default_notifications_enabled=True,
        default_quiet_hours="23:00-07:00",
        default_poll_seconds=60,
        default_match_threshold=3,
        default_hourly_limit=20,
    )


@pytest.mark.asyncio
async def test_add_company_deletes_choice_message(monkeypatch: pytest.MonkeyPatch) -> None:
    sessionmaker = DummySessionmaker()
    callback = SimpleNamespace(
        data="add:SBER",
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(chat=SimpleNamespace(id=10), answer=AsyncMock()),
        answer=AsyncMock(),
        bot=SimpleNamespace(delete_message=AsyncMock()),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"company_choice_message_id": 99})

    monkeypatch.setattr("app.bot.handlers.ensure_user", AsyncMock())
    monkeypatch.setattr("app.bot.handlers.add_subscription", AsyncMock(return_value=True))

    await add_company(callback, state, sessionmaker, make_settings())

    callback.bot.delete_message.assert_awaited_once_with(10, 99)
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_company_delete_failure_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    sessionmaker = DummySessionmaker()
    callback = SimpleNamespace(
        data="add:SBER",
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(chat=SimpleNamespace(id=10), answer=AsyncMock()),
        answer=AsyncMock(),
        bot=SimpleNamespace(
            delete_message=AsyncMock(
                side_effect=TelegramBadRequest(SimpleNamespace(), "boom")
            )
        ),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"company_choice_message_id": 99})

    monkeypatch.setattr("app.bot.handlers.ensure_user", AsyncMock())
    monkeypatch.setattr("app.bot.handlers.add_subscription", AsyncMock(return_value=True))

    await add_company(callback, state, sessionmaker, make_settings())

    callback.bot.delete_message.assert_awaited_once_with(10, 99)
    state.clear.assert_awaited_once()
