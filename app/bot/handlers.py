from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.constants import (
    ADD_COMPANY_BUTTON,
    HELP_BUTTON,
    MY_COMPANIES_BUTTON,
    SETTINGS_BUTTON,
)
from app.bot import texts
from app.bot.keyboards import (
    add_company_keyboard,
    companies_list_keyboard,
    main_menu_keyboard,
    notification_keyboard,
    settings_keyboard,
    limit_actions_keyboard,
    analysis_mode_keyboard,
    support_keyboard,
)
from app.bot.states import AddCompanyState, RemoveCompanyState, SettingsState
from app.bot.validators import validate_interval, validate_limit
from app.companies.service import CompanyDirectoryService
from app.db.repo import (
    add_subscription,
    clear_subscriptions,
    ensure_user,
    get_user,
    list_subscriptions,
    remove_subscription,
    set_hourly_limit,
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
    await message.answer(texts.HELP_TEXT, reply_markup=support_keyboard(), parse_mode=None)


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

    candidates = await company_directory.search(query or message.text)
    if not candidates:
        await message.answer("Не нашел совпадений. Попробуйте другой запрос.")
        return
    response = await message.answer(
        "Выберите компанию:",
        reply_markup=add_company_keyboard(
            [(company.ticker, company.name) for company in candidates]
        ),
    )
    await state.set_state(AddCompanyState.waiting_for_choice)
    await state.update_data(company_choice_message_id=response.message_id)


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


@router.message(F.text == SETTINGS_BUTTON)
async def settings_menu(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
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
        user = await get_user(session, message.from_user.id)
    if user is None:
        await message.answer(
            texts.build_settings_text(
                settings.default_notifications_enabled,
                settings.default_poll_seconds,
                settings.default_hourly_limit,
                settings.default_match_threshold,
            ),
            reply_markup=main_menu_keyboard(),
            parse_mode=None,
        )
        return
    await message.answer(
        texts.build_settings_text(
            user.notifications_enabled,
            user.polling_interval,
            user.hourly_limit,
            user.match_threshold,
        ),
        reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
        parse_mode=None,
    )


@router.message(F.text == HELP_BUTTON)
async def help_menu(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=support_keyboard(), parse_mode=None)


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
    state: FSMContext,
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
    data = await state.get_data()
    message_id = data.get("company_choice_message_id")
    if message_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, message_id)
        except TelegramBadRequest:
            pass
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("stop:"))
async def stop_company(callback: CallbackQuery, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    ticker = callback.data.split(":", 1)[1]
    async with sessionmaker() as session:
        await remove_subscription(session, callback.from_user.id, ticker)
    await callback.message.answer(f"{ticker} удален из подписок.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:notifications")
async def settings_notifications_toggle(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        user = await get_user(session, callback.from_user.id)
        enabled = True if user is None else not user.notifications_enabled
        await set_notifications(session, callback.from_user.id, enabled)
        user = await get_user(session, callback.from_user.id)
    text = texts.NOTIFICATIONS_ON if enabled else texts.NOTIFICATIONS_OFF
    if user is None:
        await callback.message.answer(text, reply_markup=main_menu_keyboard(), parse_mode=None)
    else:
        await callback.message.answer(
            text,
            reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
            parse_mode=None,
        )
    await callback.answer()


@router.callback_query(F.data == "settings:poll")
async def settings_poll_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        user = await get_user(session, callback.from_user.id)
    current = user.polling_interval if user else settings.default_poll_seconds
    await state.set_state(SettingsState.waiting_for_poll_interval)
    await callback.message.answer(
        f"Текущая частота проверки: {current} секунд. Введите новое значение (30–120):"
    )
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
        user = await get_user(session, callback.from_user.id)
    await callback.message.answer("Режим анализа обновлен.")
    if user is not None:
        await callback.message.answer(
            texts.build_settings_text(
                user.notifications_enabled,
                user.polling_interval,
                user.hourly_limit,
                user.match_threshold,
            ),
            reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
            parse_mode=None,
        )
    await callback.answer()


@router.callback_query(F.data == "settings:analysis")
async def settings_analysis_menu(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        user = await get_user(session, callback.from_user.id)
    if user is None:
        await callback.message.answer("Не удалось загрузить настройки.")
    else:
        await callback.message.answer(
            texts.build_analysis_mode_text(user.match_threshold),
            reply_markup=analysis_mode_keyboard(),
            parse_mode=None,
        )
    await callback.answer()


@router.callback_query(F.data == "settings:analysis:exact")
async def settings_analysis_exact(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        await update_settings(session, callback.from_user.id, match_threshold=4)
        user = await get_user(session, callback.from_user.id)
    await callback.message.answer("Режим анализа установлен: Точный.")
    if user is not None:
        await callback.message.answer(
            texts.build_settings_text(
                user.notifications_enabled,
                user.polling_interval,
                user.hourly_limit,
                user.match_threshold,
            ),
            reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
            parse_mode=None,
        )
    await callback.answer()


@router.callback_query(F.data == "settings:analysis:smart")
async def settings_analysis_smart(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        await update_settings(session, callback.from_user.id, match_threshold=3)
        user = await get_user(session, callback.from_user.id)
    await callback.message.answer("Режим анализа установлен: Умный.")
    if user is not None:
        await callback.message.answer(
            texts.build_settings_text(
                user.notifications_enabled,
                user.polling_interval,
                user.hourly_limit,
                user.match_threshold,
            ),
            reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
            parse_mode=None,
        )
    await callback.answer()


@router.callback_query(F.data == "settings:limit")
async def settings_limit_menu(
    callback: CallbackQuery,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        user = await get_user(session, callback.from_user.id)
    if user and user.hourly_limit is not None:
        await callback.message.answer(
            f"Текущий лимит: {user.hourly_limit} новостей/час.", reply_markup=limit_actions_keyboard()
        )
        await callback.answer()
        return
    await state.set_state(SettingsState.waiting_for_hourly_limit)
    await callback.message.answer("Введите лимит новостей в час (1–1000):")
    await callback.answer()


@router.callback_query(F.data == "settings:limit:change")
async def settings_limit_change(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(SettingsState.waiting_for_hourly_limit)
    await callback.message.answer("Введите новый лимит новостей в час (1–1000):")
    await callback.answer()


@router.callback_query(F.data == "settings:limit:delete")
async def settings_limit_delete(
    callback: CallbackQuery,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
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
        await set_hourly_limit(session, callback.from_user.id, None)
        user = await get_user(session, callback.from_user.id)
    await callback.message.answer("Лимит новостей удален.")
    if user is not None:
        await callback.message.answer(
            texts.build_settings_text(
                user.notifications_enabled,
                user.polling_interval,
                user.hourly_limit,
                user.match_threshold,
            ),
            reply_markup=settings_keyboard(user.notifications_enabled, user.hourly_limit),
            parse_mode=None,
        )
    await callback.answer()


@router.message(F.text.regexp(r"^\d{2}:\d{2}-\d{2}:\d{2}$"))
async def handle_quiet_hours(message: Message, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        await update_settings(session, message.from_user.id, quiet_hours=message.text)
    await message.answer("Тихий режим обновлен.")


@router.message(SettingsState.waiting_for_poll_interval)
async def handle_poll_interval(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    interval = validate_interval(message.text)
    if interval is None:
        await message.answer("Введите число от 30 до 120.")
        return
    async with sessionmaker() as session:
        await update_settings(session, message.from_user.id, polling_interval=interval)
    await state.clear()
    await message.answer(f"Готово! Частота проверки: {interval} секунд.")


@router.message(SettingsState.waiting_for_hourly_limit)
async def handle_hourly_limit(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    limit = validate_limit(message.text)
    if limit is None:
        await message.answer("Введите число от 1 до 1000.")
        return
    async with sessionmaker() as session:
        await set_hourly_limit(session, message.from_user.id, limit)
    await state.clear()
    await message.answer(f"Готово! Лимит: {limit} новостей/час.")


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
