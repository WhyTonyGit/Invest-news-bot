import json
from pathlib import Path

import pytest

from app.news.companies import load_companies


def test_load_companies_requires_fields(tmp_path: Path) -> None:
    path = tmp_path / "companies.json"
    path.write_text(json.dumps([{"ticker": "SBER"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_companies(path)


def test_dataset_contract(tmp_path: Path) -> None:
    data = [
        {
            "exchange": "MOEX",
            "ticker": "SBER",
            "name": "Сбербанк",
            "isin": None,
            "type": "share",
            "currency": "RUB",
            "aliases": ["Сбербанк", "SBER"],
            "source": {"provider": "test", "url": None, "asof_date": None},
            "updated_at": "2024-01-01T00:00:00Z",
        },
        {
            "exchange": "SPB",
            "ticker": "SBER",
            "name": "Sberbank",
            "isin": None,
            "type": "share",
            "currency": "USD",
            "aliases": ["Sberbank", "SBER"],
            "source": {"provider": "test", "url": None, "asof_date": None},
            "updated_at": "2024-01-01T00:00:00Z",
        },
    ]
    path = tmp_path / "companies.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    dataset = load_companies(path)
    seen = set()
    for record in dataset.records:
        key = (record.exchange, record.ticker)
        assert key not in seen
        seen.add(key)
