from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from rapidfuzz import process
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot import texts
from app.bot.keyboards import (
    add_company_keyboard,
    companies_list_keyboard,
    feed_mode_keyboard,
    main_menu_keyboard,
    notification_keyboard,
    settings_keyboard,
)
from app.bot.states import AddCompanyState, RemoveCompanyState
from app.db.repo import (
    add_subscription,
    clear_subscriptions,
    ensure_user,
    set_feed_mode,
    list_subscriptions,
    remove_subscription,
    set_notifications,
    update_settings,
)
from app.config import Settings
from app.news.companies import load_companies
from app.reports.service import build_report
from app.utils.normalize import normalize_text

router = Router()


@lru_cache(maxsize=1)
def _get_companies(companies_path: str) -> dict[str, list[str]]:
    path = Path(companies_path)
    dataset = load_companies(path)
    return {record.ticker: record.aliases for record in dataset.records}


def _find_candidates(query: str, companies: dict[str, list[str]]) -> list[tuple[str, str]]:
    normalized_query = normalize_text(query)
    direct = []
    for ticker, aliases in companies.items():
        if normalized_query == normalize_text(ticker):
            return [(ticker, aliases[0])]
        if any(normalized_query in normalize_text(alias) for alias in aliases):
            direct.append((ticker, aliases[0]))
    if direct:
        return direct[:5]

    choices = {ticker: " ".join(aliases) for ticker, aliases in companies.items()}
    matches = process.extract(normalized_query, choices, limit=5)
    return [(ticker, companies[ticker][0]) for ticker, score, _ in matches if score > 60]


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.START_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("report"))
async def cmd_report(
    message: Message,
    command: CommandObject,
    settings: Settings,
) -> None:
    if not command.args:
        await message.answer("Использование: /report <TICKER>")
        return
    ticker = command.args.strip().upper()
    report_text = build_report(ticker, settings.report_peers_path)
    await message.answer(report_text, reply_markup=main_menu_keyboard())


@router.message(Command("add"))
async def cmd_add(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    companies_path: str,
) -> None:
    if command.args:
        await handle_company_query(message, state, sessionmaker, settings, companies_path, command.args)
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


@router.message(F.text == "➕ Добавить компанию")
async def add_company_button(message: Message, state: FSMContext) -> None:
    await state.set_state(AddCompanyState.waiting_for_query)
    await message.answer(texts.ASK_COMPANY_TEXT)


@router.message(AddCompanyState.waiting_for_query)
async def handle_company_query(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    companies_path: str,
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
            settings.default_feed_mode,
            settings.default_digest_frequency,
            settings.summary_enabled,
        )

    await state.clear()
    companies = _get_companies(companies_path)
    candidates = _find_candidates(query or message.text, companies)
    if not candidates:
        await message.answer("Не нашел совпадений. Попробуйте другой запрос.")
        return
    await message.answer("Выберите компанию:", reply_markup=add_company_keyboard(candidates))


@router.message(F.text == "📋 Мои компании")
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


@router.message(F.text == "🔔 Включить уведомления")
async def enable_notifications(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await set_notifications(session, message.from_user.id, True)
    await message.answer(texts.NOTIFICATIONS_ON, reply_markup=main_menu_keyboard())


@router.message(F.text == "🔕 Отключить уведомления")
async def disable_notifications(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await set_notifications(session, message.from_user.id, False)
    await message.answer(texts.NOTIFICATIONS_OFF, reply_markup=main_menu_keyboard())


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message) -> None:
    await message.answer(texts.SETTINGS_TEXT, reply_markup=settings_keyboard())


@router.message(F.text == "📰 Режим ленты")
async def feed_mode_menu(message: Message) -> None:
    await message.answer("Выберите режим ленты:", reply_markup=feed_mode_keyboard())


@router.message(F.text == "❓ Помощь")
async def help_menu(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=main_menu_keyboard())


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


@router.callback_query(F.data == "settings:menu")
async def settings_menu_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(texts.SETTINGS_TEXT, reply_markup=settings_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("mode:"))
async def set_mode(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    mode = callback.data.split(":", 1)[1]
    async with sessionmaker() as session:
        await ensure_user(
            session,
            callback.from_user.id,
            settings.default_notifications_enabled,
            settings.default_quiet_hours,
            settings.default_poll_seconds,
            settings.default_match_threshold,
            settings.default_hourly_limit,
            settings.default_feed_mode,
            settings.default_digest_frequency,
            settings.summary_enabled,
        )
        await set_feed_mode(session, callback.from_user.id, mode)
    await callback.message.answer(f"Режим ленты обновлен: {mode}.", reply_markup=main_menu_keyboard())
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
            settings.default_feed_mode,
            settings.default_digest_frequency,
            settings.summary_enabled,
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
