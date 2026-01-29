from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="➕ Добавить компанию"), KeyboardButton(text="📋 Мои компании")],
        [KeyboardButton(text="🔔 Включить уведомления"), KeyboardButton(text="🔕 Отключить уведомления")],
        [KeyboardButton(text="📰 Режим ленты"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="❓ Помощь")],
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
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:menu")],
        ]
    )


def notification_keyboard(url: str, ticker: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть", url=url)],
            [InlineKeyboardButton(text=f"🚫 Не присылать {ticker}", callback_data=f"stop:{ticker}")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
        ]
    )


def market_notification_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть", url=url)],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏱ 30с", callback_data="settings:poll:30")],
            [InlineKeyboardButton(text="⏱ 60с", callback_data="settings:poll:60")],
            [InlineKeyboardButton(text="⏱ 120с", callback_data="settings:poll:120")],
            [InlineKeyboardButton(text="🌙 Тихий режим", callback_data="settings:quiet")],
            [InlineKeyboardButton(text="🎯 Точный", callback_data="settings:match:4")],
            [InlineKeyboardButton(text="🧠 Умный", callback_data="settings:match:3")],
            [InlineKeyboardButton(text="🚦 Лимит 10/ч", callback_data="settings:limit:10")],
            [InlineKeyboardButton(text="🚦 Лимит 20/ч", callback_data="settings:limit:20")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:menu")],
        ]
    )


def feed_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Watchlist", callback_data="mode:watchlist")],
            [InlineKeyboardButton(text="🌍 Market", callback_data="mode:market")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:menu")],
        ]
    )


def help_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/its_for_git")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:menu")],
        ]
    )
