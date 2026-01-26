from app.utils.normalize import normalize_text


def test_normalize_text() -> None:
    assert normalize_text("ЛУКОЙЛ!!!") == "лукойл"
    assert normalize_text("  МосБиржа\n\t") == "мосбиржа"
