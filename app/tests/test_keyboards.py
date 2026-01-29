from app.bot.constants import (
    BUTTON_ADD_COMPANY,
    BUTTON_FEED_MODE,
    BUTTON_HELP,
    BUTTON_MY_COMPANIES,
    BUTTON_NOTIFICATIONS_OFF,
    BUTTON_NOTIFICATIONS_ON,
    BUTTON_SETTINGS,
)
from app.bot.keyboards import feed_mode_keyboard, main_menu_keyboard


def test_main_menu_keyboard_has_feed_mode() -> None:
    keyboard = main_menu_keyboard()
    buttons = [button.text for row in keyboard.keyboard for button in row]
    assert BUTTON_FEED_MODE in buttons
    assert BUTTON_ADD_COMPANY in buttons
    assert BUTTON_MY_COMPANIES in buttons
    assert BUTTON_NOTIFICATIONS_ON in buttons
    assert BUTTON_NOTIFICATIONS_OFF in buttons
    assert BUTTON_SETTINGS in buttons
    assert BUTTON_HELP in buttons
    assert len(buttons) == len(set(buttons))


def test_feed_mode_keyboard_buttons() -> None:
    keyboard = feed_mode_keyboard()
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "📌 Watchlist" in texts
    assert "🌍 Market" in texts
