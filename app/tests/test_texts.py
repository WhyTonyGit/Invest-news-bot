from app.bot.texts import START_TEXT, build_settings_text


def test_start_message_contains_key_points() -> None:
    text = START_TEXT.lower()
    assert "новост" in text
    assert "/add" in text
    assert "/list" in text
    assert "настроек" in text
    assert "помощ" in text


def test_build_settings_text_contains_explanations() -> None:
    text = build_settings_text(True, 60, None, 3)
    assert "Уведомления" in text
    assert "Частота проверки" in text
    assert "Лимит" in text
    assert "Режим анализа" in text
    assert "Тихий режим" in text


def test_build_settings_text_shows_current_analysis_mode() -> None:
    text = build_settings_text(True, 60, None, 4)
    assert "Точный" in text
