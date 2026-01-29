from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CompanyRecord:
    exchange: str
    ticker: str
    name: str
    isin: str | None
    type: str
    currency: str | None
    aliases: list[str]
    source: dict[str, Any]
    updated_at: str


@dataclass(frozen=True)
class CompaniesDataset:
    records: list[CompanyRecord]

    def by_ticker(self) -> dict[str, CompanyRecord]:
        return {record.ticker: record for record in self.records}

    def aliases_map(self) -> dict[str, list[str]]:
        return {record.ticker: record.aliases for record in self.records}


REQUIRED_FIELDS = {
    "exchange",
    "ticker",
    "name",
    "isin",
    "type",
    "currency",
    "aliases",
    "source",
    "updated_at",
}


def load_companies(path: Path) -> CompaniesDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Companies dataset must be a list")
    records: list[CompanyRecord] = []
    for item in payload:
        if not REQUIRED_FIELDS.issubset(item.keys()):
            missing = REQUIRED_FIELDS.difference(item.keys())
            raise ValueError(f"Missing fields in company record: {missing}")
        records.append(
            CompanyRecord(
                exchange=item["exchange"],
                ticker=item["ticker"],
                name=item["name"],
                isin=item.get("isin"),
                type=item.get("type", "unknown"),
                currency=item.get("currency"),
                aliases=list(item.get("aliases", [])),
                source=item.get("source", {}),
                updated_at=item["updated_at"],
            )
        )
    return CompaniesDataset(records=records)
