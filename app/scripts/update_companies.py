from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BASE_DIR / "data" / "companies.json"

MOEX_BASE = "https://iss.moex.com/iss/engines/stock/markets/shares/boards"
SPB_LISTING_URL = "https://spbexchange.ru/ru/listing/securities/list/"

BOARD_IDS = ["TQBR", "TQTF", "TQTD", "TQTE"]


def _build_aliases(ticker: str, name: str, shortname: str | None) -> list[str]:
    aliases = {ticker, f"${ticker}", name}
    if shortname:
        aliases.add(shortname)
    return sorted({alias for alias in aliases if alias})


def _map_type(secname: str | None) -> str:
    if not secname:
        return "unknown"
    normalized = secname.lower()
    if "etf" in normalized or "паи" in normalized:
        return "etf"
    if "депозитар" in normalized or "dr" in normalized:
        return "depositary_receipt"
    if "облигац" in normalized:
        return "bond"
    return "share"


async def fetch_moex_board(session: aiohttp.ClientSession, board: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    start = 0
    while True:
        url = (
            f"{MOEX_BASE}/{board}/securities.json?iss.meta=off&iss.only=securities"
            "&securities.columns=SECID,SHORTNAME,NAME,ISIN,SECNAME,CURRENCY,FACEUNIT"
            f"&start={start}"
        )
        async with session.get(url) as response:
            response.raise_for_status()
            payload = await response.json()
        data = payload.get("securities", {})
        items = data.get("data", [])
        columns = data.get("columns", [])
        if not items:
            break
        for row in items:
            row_map = dict(zip(columns, row))
            ticker = str(row_map.get("SECID", "")).upper()
            if not ticker:
                continue
            name = str(row_map.get("NAME") or row_map.get("SHORTNAME") or ticker).strip()
            shortname = str(row_map.get("SHORTNAME") or "").strip() or None
            records.append(
                {
                    "exchange": "MOEX",
                    "ticker": ticker,
                    "name": name,
                    "isin": row_map.get("ISIN"),
                    "type": _map_type(row_map.get("SECNAME")),
                    "currency": row_map.get("CURRENCY") or row_map.get("FACEUNIT"),
                    "aliases": _build_aliases(ticker, name, shortname),
                    "source": {
                        "provider": "moex_iss",
                        "url": url,
                        "asof_date": None,
                    },
                }
            )
        start += len(items)
    return records


async def fetch_moex(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for board in BOARD_IDS:
        results.extend(await fetch_moex_board(session, board))
    return results


def _extract_spb_asof(text: str) -> str | None:
    match = re.search(r"по\\s+состоянию\\s+на\\s+([\\d.]+)", text, re.IGNORECASE)
    return match.group(1) if match else None


async def fetch_spb(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    async with session.get(SPB_LISTING_URL) as response:
        response.raise_for_status()
        html = await response.text()
    soup = BeautifulSoup(html, "html.parser")
    asof_date = _extract_spb_asof(soup.get_text(" "))

    table = None
    for candidate in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in candidate.find_all("th")]
        if any("тикер" in header for header in headers):
            table = candidate
            break

    records: list[dict[str, Any]] = []
    if table:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            if len(cols) < 2:
                continue
            ticker, name = cols[0].upper(), cols[1]
            if not ticker:
                continue
            records.append(
                {
                    "exchange": "SPB",
                    "ticker": ticker,
                    "name": name,
                    "isin": None,
                    "type": "share",
                    "currency": None,
                    "aliases": _build_aliases(ticker, name, None),
                    "source": {
                        "provider": "spb_exchange",
                        "url": SPB_LISTING_URL,
                        "asof_date": asof_date,
                    },
                }
            )
        return records

    file_link = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().endswith((".xlsx", ".xls")):
            file_link = href if href.startswith("http") else f"https://spbexchange.ru{href}"
            break

    if not file_link:
        return records

    async with session.get(file_link) as response:
        response.raise_for_status()
        content = await response.read()

    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pandas is required to parse Excel listing files") from exc

    import io

    df = pd.read_excel(io.BytesIO(content))
    for _, row in df.iterrows():
        ticker = str(row.get("Ticker") or row.get("тикер") or "").upper()
        name = str(row.get("Company") or row.get("Эмитент") or row.get("Компания") or "").strip()
        if not ticker:
            continue
        records.append(
            {
                "exchange": "SPB",
                "ticker": ticker,
                "name": name or ticker,
                "isin": None,
                "type": "share",
                "currency": None,
                "aliases": _build_aliases(ticker, name or ticker, None),
                "source": {
                    "provider": "spb_exchange",
                    "url": file_link,
                    "asof_date": asof_date,
                },
            }
        )
    return records


def merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    updated_at = datetime.now(timezone.utc).isoformat()
    for record in records:
        key = (record["exchange"], record["ticker"])
        if key in merged:
            continue
        record["updated_at"] = updated_at
        merged[key] = record
    return list(merged.values())


async def main(output_path: Path) -> None:
    async with aiohttp.ClientSession() as session:
        moex = await fetch_moex(session)
        spb = await fetch_spb(session)
    merged = merge_records(moex + spb)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(merged)} records to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update companies dataset from MOEX and SPB sources")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output JSON file")
    args = parser.parse_args()
    asyncio.run(main(Path(args.output)))
