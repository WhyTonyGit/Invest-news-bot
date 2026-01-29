from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import handlers
from app.bot.handlers import cmd_add


@pytest.mark.asyncio
async def test_cmd_add_calls_handle_company_query_once(monkeypatch: pytest.MonkeyPatch) -> None:
    message = SimpleNamespace()
    command = SimpleNamespace(args="SBER")
    state = SimpleNamespace()
    sessionmaker = SimpleNamespace()
    settings = SimpleNamespace()
    company_directory = object()

    handle_company_query = AsyncMock()
    monkeypatch.setattr(handlers, "handle_company_query", handle_company_query)

    await cmd_add(message, command, state, sessionmaker, settings, company_directory)

    handle_company_query.assert_awaited_once()
    args = handle_company_query.await_args.args
    assert args[4] is company_directory
    assert args[5] == "SBER"
