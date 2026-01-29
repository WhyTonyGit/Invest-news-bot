from __future__ import annotations

import json
from pathlib import Path
from statistics import median

BASE_DIR = Path(__file__).resolve().parents[1]
FINANCIALS_PATH = BASE_DIR / "data" / "financials_ru.json"

METRIC_LABELS = {
    "revenue": "Выручка",
    "net_income": "Чистая прибыль",
    "ebitda": "EBITDA",
    "fcf": "Свободный денежный поток",
    "net_debt_ebitda": "NetDebt/EBITDA",
}


def build_report(ticker: str, peers_path: str) -> str:
    financials = _load_json(FINANCIALS_PATH)
    record = financials.get(ticker)
    if not record:
        return f"Нет данных по {ticker}. Попробуйте другой тикер."

    currency = record.get("currency", "")
    lines = [f"<b>Отчетность {ticker}</b>"]
    metrics = record.get("metrics", {})
    for key, label in METRIC_LABELS.items():
        if key not in metrics:
            continue
        item = metrics[key]
        value = item.get("value")
        prev = item.get("prev")
        period = item.get("period", "")
        delta = ""
        if prev is not None and value is not None:
            try:
                delta = f" (Δ {value - prev:+})"
            except TypeError:
                delta = ""
        suffix = f" {currency}" if key != "net_debt_ebitda" and currency else ""
        lines.append(f"• {label}: {value}{suffix} {period}{delta}")

    peer_line = _build_peer_compare(ticker, metrics, peers_path)
    if peer_line:
        lines.append("\nСравнение с сектором:")
        lines.extend(peer_line)

    return "\n".join(lines)


def _build_peer_compare(ticker: str, metrics: dict, peers_path: str) -> list[str]:
    peers = _load_json(Path(peers_path)).get(ticker, [])
    if not peers:
        return []
    financials = _load_json(FINANCIALS_PATH)
    lines: list[str] = []
    for key, label in METRIC_LABELS.items():
        value = metrics.get(key, {}).get("value")
        peer_values = [financials.get(peer, {}).get("metrics", {}).get(key, {}).get("value") for peer in peers]
        peer_values = [val for val in peer_values if val is not None]
        if value is None or not peer_values:
            continue
        peer_median = median(peer_values)
        comparison = "лучше" if value >= peer_median else "хуже"
        lines.append(f"• {label}: {comparison} медианы сектора ({peer_median})")
    return lines


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
