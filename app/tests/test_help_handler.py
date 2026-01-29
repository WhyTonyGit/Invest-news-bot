from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.handlers import cmd_help, help_menu


@pytest.mark.asyncio
async def test_help_handler_mentions_support() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    await cmd_help(message)
    message.answer.assert_awaited()
    args, kwargs = message.answer.await_args
    assert "@its_for_git" in args[0]


@pytest.mark.asyncio
async def test_help_menu_mentions_support() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    await help_menu(message)
    message.answer.assert_awaited()
    args, kwargs = message.answer.await_args
    assert "@its_for_git" in args[0]
