from unittest.mock import AsyncMock

import pytest

from app.bot.constants import SUPPORT_HANDLE
from app.bot.handlers import help_menu
from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import HELP_TEXT


@pytest.mark.asyncio
async def test_help_button() -> None:
    message = AsyncMock()

    await help_menu(message)

    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert SUPPORT_HANDLE in args[0]
    assert HELP_TEXT in args[0]
    assert kwargs.get("reply_markup") is not None
    assert kwargs.get("parse_mode") is None


def test_main_menu_unique_buttons() -> None:
    keyboard = main_menu_keyboard()
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert len(texts) == len(set(texts))
