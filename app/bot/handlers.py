from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.constants import (
    ADD_COMPANY_BUTTON,
    HELP_BUTTON,
    MY_COMPANIES_BUTTON,
    NOTIFICATIONS_OFF_BUTTON,
    NOTIFICATIONS_ON_BUTTON,
    SETTINGS_BUTTON,
)
from app.bot import texts
from app.bot.keyboards import (
    add_company_keyboard,
    companies_list_keyboard,
    main_menu_keyboard,
    notification_keyboard,
    settings_keyboard,
    support_keyboard,
)
from app.bot.states import AddCompanyState, RemoveCompanyState
from app.companies.service import CompanyDirectoryService
from app.db.repo import (
    add_subscription,
    clear_subscriptions,
    ensure_user,
    list_subscriptions,
    remove_subscription,
    set_notifications,
    update_settings,
)
from app.config import Settings

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.START_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=support_keyboard())


@router.message(Command("add"))
async def cmd_add(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    company_directory: CompanyDirectoryService,
) -> None:
    if command.args:
        await handle_company_query(
            message, state, sessionmaker, settings, company_directory, command.args
        )
        return
    await state.set_state(AddCompanyState.waiting_for_query)
    await message.answer(texts.ASK_COMPANY_TEXT)


@router.message(Command("list"))
async def cmd_list(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        subs = await list_subscriptions(session, message.from_user.id)
    if not subs:
        await message.answer(texts.NO_COMPANIES_TEXT, reply_markup=main_menu_keyboard())
        return
    lines = ["Ваши компании:"]
    for sub in subs:
        lines.append(f"• {sub.ticker}")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@router.message(F.text == ADD_COMPANY_BUTTON)
async def add_company_button(message: Message, state: FSMContext) -> None:
    await state.set_state(AddCompanyState.waiting_for_query)
    await message.answer(texts.ASK_COMPANY_TEXT)


@router.message(AddCompanyState.waiting_for_query)
async def handle_company_query(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    company_directory: CompanyDirectoryService,
    query: str | None = None,
) -> None:
    async with sessionmaker() as session:
        await ensure_user(
            session,
            message.from_user.id,
            settings.default_notifications_enabled,
            settings.default_quiet_hours,
            settings.default_poll_seconds,
            settings.default_match_threshold,
            settings.default_hourly_limit,
        )

    await state.clear()
    candidates = await company_directory.search(query or message.text)
    if not candidates:
        await message.answer("Не нашел совпадений. Попробуйте другой запрос.")
        return
    await message.answer(
        "Выберите компанию:",
        reply_markup=add_company_keyboard(
            [(company.ticker, company.name) for company in candidates]
        ),
    )


@router.message(F.text == MY_COMPANIES_BUTTON)
async def my_companies(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        subs = await list_subscriptions(session, message.from_user.id)
    if not subs:
        await message.answer(texts.NO_COMPANIES_TEXT, reply_markup=main_menu_keyboard())
        return
    lines = ["Ваши компании:"]
    for sub in subs:
        lines.append(f"• {sub.ticker}")
    await message.answer("\n".join(lines), reply_markup=companies_list_keyboard())


@router.message(F.text == NOTIFICATIONS_ON_BUTTON)
async def enable_notifications(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await set_notifications(session, message.from_user.id, True)
    await message.answer(texts.NOTIFICATIONS_ON, reply_markup=main_menu_keyboard())


@router.message(F.text == NOTIFICATIONS_OFF_BUTTON)
async def disable_notifications(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await set_notifications(session, message.from_user.id, False)
    await message.answer(texts.NOTIFICATIONS_OFF, reply_markup=main_menu_keyboard())


@router.message(F.text == SETTINGS_BUTTON)
async def settings_menu(message: Message) -> None:
    await message.answer(texts.SETTINGS_TEXT, reply_markup=settings_keyboard())


@router.message(F.text == HELP_BUTTON)
async def help_menu(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=support_keyboard())


@router.callback_query(F.data == "subs:remove")
async def remove_subscription_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RemoveCompanyState.waiting_for_ticker)
    await callback.message.answer("Введите тикер для удаления, например: LKOH")
    await callback.answer()


@router.callback_query(F.data == "subs:clear")
async def clear_subs(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await clear_subscriptions(session, callback.from_user.id)
    await callback.message.answer("Подписки очищены.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back:menu")
async def back_to_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_company(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    ticker = callback.data.split(":", 1)[1]
    async with sessionmaker() as session:
        await ensure_user(
            session,
            callback.from_user.id,
            settings.default_notifications_enabled,
            settings.default_quiet_hours,
            settings.default_poll_seconds,
            settings.default_match_threshold,
            settings.default_hourly_limit,
        )
        added = await add_subscription(session, callback.from_user.id, ticker)
    if added:
        await callback.message.answer(f"✅ {ticker} добавлен.", reply_markup=main_menu_keyboard())
    else:
        await callback.message.answer(f"{ticker} уже в списке.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("stop:"))
async def stop_company(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    ticker = callback.data.split(":", 1)[1]
    async with sessionmaker() as session:
        await remove_subscription(session, callback.from_user.id, ticker)
    await callback.message.answer(f"{ticker} удален из подписок.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("settings:poll:"))
async def settings_poll(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    poll = int(callback.data.split(":")[-1])
    async with sessionmaker() as session:
        await update_settings(session, callback.from_user.id, polling_interval=poll)
    await callback.message.answer(f"Частота обновления: {poll} сек.")
    await callback.answer()


@router.callback_query(F.data == "settings:quiet")
async def settings_quiet(callback: CallbackQuery) -> None:
    await callback.message.answer("Тихий режим: укажите часы в формате 23:00-07:00")
    await callback.answer()


@router.callback_query(F.data.startswith("settings:match:"))
async def settings_match(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    threshold = int(callback.data.split(":")[-1])
    async with sessionmaker() as session:
        await update_settings(session, callback.from_user.id, match_threshold=threshold)
    await callback.message.answer("Уровень совпадения обновлен.")
    await callback.answer()


@router.callback_query(F.data.startswith("settings:limit:"))
async def settings_limit(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    limit = int(callback.data.split(":")[-1])
    async with sessionmaker() as session:
        await update_settings(session, callback.from_user.id, hourly_limit=limit)
    await callback.message.answer(f"Лимит {limit} новостей/час установлен.")
    await callback.answer()


@router.message(F.text.regexp(r"^\d{2}:\d{2}-\d{2}:\d{2}$"))
async def handle_quiet_hours(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await update_settings(session, message.from_user.id, quiet_hours=message.text)
    await message.answer("Тихий режим обновлен.")


@router.message(RemoveCompanyState.waiting_for_ticker)
async def remove_by_ticker(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    ticker = message.text.strip().upper()
    async with sessionmaker() as session:
        await remove_subscription(session, message.from_user.id, ticker)
    await state.clear()
    await message.answer("Готово.", reply_markup=main_menu_keyboard())
