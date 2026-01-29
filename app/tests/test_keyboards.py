from app.bot.constants import SETTINGS_ANALYSIS_BUTTON
from app.bot.keyboards import (
    companies_list_keyboard,
    notification_keyboard,
    settings_keyboard,
)


def test_settings_keyboard_no_back_button() -> None:
    keyboard = settings_keyboard(True, None)
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Назад" not in " ".join(texts)


def test_settings_keyboard_shows_limit_button_correctly() -> None:
    no_limit = settings_keyboard(True, None)
    texts = [button.text for row in no_limit.inline_keyboard for button in row]
    assert "Установить лимит" in " ".join(texts)
    assert "Лимит:" not in " ".join(texts)

    with_limit = settings_keyboard(True, 10)
    texts = [button.text for row in with_limit.inline_keyboard for button in row]
    assert "Лимит: 10/час" in " ".join(texts)
    assert "Установить лимит" not in " ".join(texts)


def test_settings_keyboard_contains_analysis_mode_button() -> None:
    keyboard = settings_keyboard(True, None)
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert SETTINGS_ANALYSIS_BUTTON in texts
    assert "Точный" not in " ".join(texts)
    assert "Умный" not in " ".join(texts)


def test_my_companies_keyboard_no_back_button() -> None:
    keyboard = companies_list_keyboard()
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Назад" not in " ".join(texts)


def test_news_keyboard_has_no_settings_button() -> None:
    keyboard = notification_keyboard("https://example.com", "SBER")
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Настройки" not in " ".join(texts)
