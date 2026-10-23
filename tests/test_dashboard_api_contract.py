import os
from datetime import date
from urllib.parse import urlparse

import psycopg
import pytest

import app.main as main


def test_summary_reports_period_mismatch_and_applies_filters(monkeypatch):
    captured = {}

    def fake_fetch_one(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return {
            "jumlah_divisi": 1,
            "jumlah_estate": 1,
            "budget_report_date": date(2026, 10, 20),
            "actual_report_date": date(2026, 10, 19),
            "tanggal_laporan_anggaran": date(2026, 10, 20),
            "tanggal_laporan_realisasi": date(2026, 10, 19),
            "total_anggaran_ton": 100,
            "total_realisasi_ton": 90,
            "selisih_ton": -10,
            "pencapaian_persen": 90,
        }

    monkeypatch.setattr(main, "fetch_one", fake_fetch_one)
    result = main.summary("MAGE", "MAGE1")

    assert result["period_status"] == "mismatch"
    assert "berbeda" in result["period_warning"]
    assert "estate_code = %s" in captured["sql"]
    assert "division_code = %s" in captured["sql"]
    assert captured["params"] == ["MAGE", "MAGE1"]


def test_summary_reports_incomplete_period_when_data_is_missing(monkeypatch):
    monkeypatch.setattr(
        main,
        "fetch_one",
        lambda *args, **kwargs: {
            "jumlah_divisi": 24,
            "jumlah_estate": 6,
            "budget_report_date": date(2026, 10, 20),
            "actual_report_date": None,
        },
    )

    result = main.summary(None, None)

    assert result["period_status"] == "incomplete"
    assert "belum lengkap" in result["period_warning"]


def test_estate_and_division_endpoints_use_same_filters(monkeypatch):
    calls = []

    def fake_fetch_all(sql, params=None):
        calls.append((sql, params))
        return []

    monkeypatch.setattr(main, "fetch_all", fake_fetch_all)

    estate_result = main.estates("bhpe", "bhpe2")
    division_result = main.divisions("bhpe", "bhpe2")

    assert estate_result == {"count": 0, "items": []}
    assert division_result == {"count": 0, "items": []}
    assert len(calls) == 2
    for sql, params in calls:
        assert "estate_code = %s" in sql
        assert "division_code = %s" in sql
        assert params == ["BHPE", "BHPE2"]


@pytest.mark.skipif(
    urlparse(os.getenv("DATABASE_URL", "")).path.lstrip("/")
    != "pems_test_import",
    reason="Kontrak SQL hanya boleh berjalan pada pems_test_import.",
)
def test_dashboard_view_and_summary_contract_on_test_database():
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'v_pems_comparison_division'
            """)
            columns = {row[0] for row in cursor.fetchall()}
            assert {
                "budget_report_date",
                "actual_report_date",
                "budget_ton",
                "actual_ton",
                "variance_ton",
                "achievement_pct",
            } <= columns
            cursor.execute("""
                SELECT COUNT(*)
                FROM v_pems_comparison_division
                WHERE variance_ton <> actual_ton - budget_ton
                   OR (budget_ton = 0 AND achievement_pct IS NOT NULL)
            """)
            assert cursor.fetchone()[0] == 0

    result = main.summary(None, None)
    assert {
        "period_status",
        "period_warning",
        "tanggal_laporan_anggaran",
        "tanggal_laporan_realisasi",
    } <= result.keys()
