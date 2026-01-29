from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.constants import (
    ADD_COMPANY_BUTTON,
    HELP_BUTTON,
    MY_COMPANIES_BUTTON,
    SETTINGS_BUTTON,
    SETTINGS_LIMIT_CHANGE_BUTTON,
    SETTINGS_LIMIT_DELETE_BUTTON,
    SETTINGS_LIMIT_SET_BUTTON,
    SETTINGS_LIMIT_VALUE_TEMPLATE,
    SETTINGS_ANALYSIS_BUTTON,
    SETTINGS_MATCH_ACCURATE_BUTTON,
    SETTINGS_MATCH_SMART_BUTTON,
    SETTINGS_NOTIFICATIONS_OFF,
    SETTINGS_NOTIFICATIONS_ON,
    SETTINGS_POLLING_BUTTON,
    SETTINGS_QUIET_BUTTON,
    SUPPORT_URL,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=ADD_COMPANY_BUTTON), KeyboardButton(text=MY_COMPANIES_BUTTON)],
        [KeyboardButton(text=SETTINGS_BUTTON), KeyboardButton(text=HELP_BUTTON)],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def add_company_keyboard(options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"✅ {name}", callback_data=f"add:{ticker}")]
        for ticker, name in options
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def companies_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➖ Удалить", callback_data="subs:remove")],
            [InlineKeyboardButton(text="🧹 Очистить", callback_data="subs:clear")],
        ]
    )


def notification_keyboard(url: str, ticker: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть", url=url)],
            [InlineKeyboardButton(text=f"🚫 Не присылать {ticker}", callback_data=f"stop:{ticker}")],
        ]
    )


def settings_keyboard(notifications_enabled: bool, hourly_limit: int | None) -> InlineKeyboardMarkup:
    notifications_text = SETTINGS_NOTIFICATIONS_ON if notifications_enabled else SETTINGS_NOTIFICATIONS_OFF
    limit_text = (
        SETTINGS_LIMIT_VALUE_TEMPLATE.format(limit=hourly_limit)
        if hourly_limit is not None
        else SETTINGS_LIMIT_SET_BUTTON
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=notifications_text, callback_data="settings:notifications")],
            [InlineKeyboardButton(text=SETTINGS_POLLING_BUTTON, callback_data="settings:poll")],
            [InlineKeyboardButton(text=SETTINGS_QUIET_BUTTON, callback_data="settings:quiet")],
            [InlineKeyboardButton(text=SETTINGS_ANALYSIS_BUTTON, callback_data="settings:analysis")],
            [InlineKeyboardButton(text=limit_text, callback_data="settings:limit")],
        ]
    )


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Написать в поддержку", url=SUPPORT_URL)]]
    )


def limit_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=SETTINGS_LIMIT_CHANGE_BUTTON, callback_data="settings:limit:change")],
            [InlineKeyboardButton(text=SETTINGS_LIMIT_DELETE_BUTTON, callback_data="settings:limit:delete")],
        ]
    )


def analysis_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=SETTINGS_MATCH_ACCURATE_BUTTON, callback_data="settings:analysis:exact")],
            [InlineKeyboardButton(text=SETTINGS_MATCH_SMART_BUTTON, callback_data="settings:analysis:smart")],
        ]
    )
