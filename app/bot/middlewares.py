from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.companies.service import CompanyDirectoryService
from app.config import Settings


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        settings: Settings,
        directory: CompanyDirectoryService,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._directory = directory

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["sessionmaker"] = self._sessionmaker
        data["settings"] = self._settings
        data["company_directory"] = self._directory
        return await handler(event, data)
