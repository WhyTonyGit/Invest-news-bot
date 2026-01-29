from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import texts
from app.bot.handlers import (
    handle_hourly_limit,
    handle_poll_interval,
    settings_limit_menu,
    settings_notifications_toggle,
)
from app.bot.keyboards import limit_actions_keyboard
from app.bot.states import SettingsState


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
async def test_settings_notifications_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    sessionmaker = DummySessionmaker()
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )

    ensure_user = AsyncMock()
    get_user = AsyncMock(
        side_effect=[
            SimpleNamespace(notifications_enabled=True, hourly_limit=None),
            SimpleNamespace(notifications_enabled=False, hourly_limit=None),
        ]
    )
    set_notifications = AsyncMock()

    monkeypatch.setattr("app.bot.handlers.ensure_user", ensure_user)
    monkeypatch.setattr("app.bot.handlers.get_user", get_user)
    monkeypatch.setattr("app.bot.handlers.set_notifications", set_notifications)

    await settings_notifications_toggle(callback, sessionmaker, make_settings())

    set_notifications.assert_awaited_once_with(SimpleNamespace(), 1, False)
    assert texts.NOTIFICATIONS_OFF in callback.message.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_settings_limit_menu_shows_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    sessionmaker = DummySessionmaker()
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )
    state = AsyncMock()

    monkeypatch.setattr("app.bot.handlers.ensure_user", AsyncMock())
    monkeypatch.setattr(
        "app.bot.handlers.get_user",
        AsyncMock(return_value=SimpleNamespace(hourly_limit=10)),
    )

    await settings_limit_menu(callback, state, sessionmaker, make_settings())

    args, kwargs = callback.message.answer.call_args
    assert "Текущий лимит" in args[0]
    assert isinstance(kwargs.get("reply_markup"), type(limit_actions_keyboard()))


@pytest.mark.asyncio
async def test_handle_poll_interval_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    message = SimpleNamespace(text="60", answer=AsyncMock(), from_user=SimpleNamespace(id=1))
    state = AsyncMock()
    sessionmaker = DummySessionmaker()
    update_settings = AsyncMock()
    monkeypatch.setattr("app.bot.handlers.update_settings", update_settings)

    await handle_poll_interval(message, state, sessionmaker)

    update_settings.assert_awaited_once()
    state.clear.assert_awaited_once()
    assert "Готово" in message.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_hourly_limit_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    message = SimpleNamespace(text="10", answer=AsyncMock(), from_user=SimpleNamespace(id=1))
    state = AsyncMock()
    sessionmaker = DummySessionmaker()
    set_hourly_limit = AsyncMock()
    monkeypatch.setattr("app.bot.handlers.set_hourly_limit", set_hourly_limit)

    await handle_hourly_limit(message, state, sessionmaker)

    set_hourly_limit.assert_awaited_once()
    state.clear.assert_awaited_once()
    assert "Лимит" in message.answer.call_args.args[0]
