from app.news.dedupe import canonical_hash, is_similar


def test_canonical_hash_changes() -> None:
    hash_a = canonical_hash("Лукойл обновил прогноз", "подробности", "https://example.com/a")
    hash_b = canonical_hash("Лукойл обновил прогноз", "", "https://example.com/a")
    assert hash_a != hash_b


def test_canonical_hash_url_changes() -> None:
    hash_a = canonical_hash("Лукойл обновил прогноз", "подробности", "https://example.com/a")
    hash_b = canonical_hash("Лукойл обновил прогноз", "подробности", "https://example.com/b")
    assert hash_a != hash_b


def test_is_similar_titles() -> None:
    assert is_similar("Лукойл обновил прогноз", "Лукойл обновил прогноз на 2024 год")
