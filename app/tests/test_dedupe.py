from app.news.dedupe import canonical_hash, is_similar


def test_canonical_hash_changes() -> None:
    hash_a = canonical_hash("Лукойл обновил прогноз", "подробности")
    hash_b = canonical_hash("Лукойл обновил прогноз", "")
    assert hash_a != hash_b


def test_is_similar_titles() -> None:
    assert is_similar("Лукойл обновил прогноз", "Лукойл обновил прогноз на 2024 год")
