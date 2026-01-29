from app.reports.service import build_report


def test_report_service_returns_text() -> None:
    report = build_report("SBER", "app/data/peers.json")
    assert "Отчетность" in report
    assert "Выручка" in report
