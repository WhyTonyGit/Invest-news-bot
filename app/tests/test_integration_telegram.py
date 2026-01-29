import os

import pytest
from aiogram import Bot

pytest_asyncio = pytest.importorskip("pytest_asyncio")


@pytest.mark.integration
@pytest_asyncio.fixture
async def bot() -> Bot:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("TELEGRAM_BOT_TOKEN not set")
    bot_instance = Bot(token)
    yield bot_instance
    await bot_instance.session.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_send_message(bot: Bot) -> None:
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        pytest.skip("TELEGRAM_CHAT_ID not set")
    await bot.send_message(chat_id, "SMOKE: help")
