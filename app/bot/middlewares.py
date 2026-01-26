from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        settings: Settings,
        companies_path: str,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._companies_path = companies_path

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["sessionmaker"] = self._sessionmaker
        data["settings"] = self._settings
        data["companies_path"] = self._companies_path
        return await handler(event, data)
