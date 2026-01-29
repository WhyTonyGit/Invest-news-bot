from app.bot.texts import START_TEXT


def test_start_message_contains_key_points() -> None:
    text = START_TEXT.lower()
    assert "новост" in text
    assert "/add" in text
    assert "/list" in text
    assert "настроек" in text
    assert "помощ" in text
