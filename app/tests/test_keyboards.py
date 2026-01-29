from app.bot.keyboards import feed_mode_keyboard, main_menu_keyboard


def test_main_menu_keyboard_has_feed_mode() -> None:
    keyboard = main_menu_keyboard()
    buttons = [button.text for row in keyboard.keyboard for button in row]
    assert "📰 Режим ленты" in buttons
    assert len(buttons) == len(set(buttons))


def test_feed_mode_keyboard_buttons() -> None:
    keyboard = feed_mode_keyboard()
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "📌 Watchlist" in texts
    assert "🌍 Market" in texts
