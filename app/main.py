import os
from contextlib import closing
from datetime import date

import psycopg
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from app.production_periods import serialize_production_periods

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///pems_db")

app = FastAPI(
    title="PEMS API",
    description="Monitoring Anggaran dan Realisasi Produksi",
    version="0.1.0",
)


def fetch_all(sql, params=None):
    try:
        with closing(
            psycopg.connect(DATABASE_URL, row_factory=dict_row)
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Database PEMS tidak dapat diakses.",
        ) from exc


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def add_period_metadata(row):
    """Tambahkan status periode tanpa mengubah nilai bisnis tersimpan."""
    if not row:
        return row
    result = dict(row)
    budget_date = result.get("budget_report_date") or result.get(
        "tanggal_laporan_anggaran"
    )
    actual_date = result.get("actual_report_date") or result.get(
        "tanggal_laporan_realisasi"
    )
    if not budget_date or not actual_date:
        result["period_status"] = "incomplete"
        result["period_warning"] = (
            "Periode belum lengkap; budget dan realisasi belum sama-sama tersedia."
        )
    elif budget_date == actual_date:
        result["period_status"] = "aligned"
        result["period_warning"] = "Periode budget dan realisasi selaras."
    else:
        result["period_status"] = "mismatch"
        result["period_warning"] = (
            "Tanggal laporan budget dan realisasi berbeda; "
            "perbandingan tetap ditampilkan untuk verifikasi."
        )
    return result


def add_period_metadata_many(rows):
    return [add_period_metadata(row) for row in rows]


@app.get("/")
def root():
    return {
        "application": "PEMS",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    row = fetch_one("""
        SELECT current_database() AS database,
               CURRENT_TIMESTAMP AS checked_at
    """)
    return {
        "status": "ok",
        "database": row["database"],
        "checked_at": row["checked_at"],
    }


@app.get("/api/production/periods")
def production_periods(as_of: date | None = Query(default=None)):
    """Return stable date windows for production KPI aggregation."""
    report_date = as_of or date.today()
    source = "query" if as_of else "server_date"
    return serialize_production_periods(report_date, source)


@app.get("/api/summary")
def summary(
    estate_code: str | None = Query(default=None, max_length=10),
    division_code: str | None = Query(default=None, max_length=20),
):
    filters = []
    params = []
    if estate_code:
        filters.append("estate_code = %s")
        params.append(estate_code.upper())
    if division_code:
        filters.append("division_code = %s")
        params.append(division_code.upper())
    where = "WHERE " + " AND ".join(filters) if filters else ""
    row = fetch_one(f"""
        SELECT
            COUNT(*)::INTEGER AS jumlah_divisi,
            COUNT(DISTINCT estate_code)::INTEGER AS jumlah_estate,
            MIN(budget_report_date) AS budget_report_date,
            MIN(actual_report_date) AS actual_report_date,
            MIN(budget_report_date) AS tanggal_laporan_anggaran,
            MIN(actual_report_date) AS tanggal_laporan_realisasi,
            COALESCE(SUM(budget_ton), 0) AS total_anggaran_ton,
            COALESCE(SUM(actual_ton), 0) AS total_realisasi_ton,
            COALESCE(SUM(variance_ton), 0) AS selisih_ton,
            ROUND(
                100.0 * SUM(actual_ton) /
                NULLIF(SUM(budget_ton), 0),
                2
            ) AS pencapaian_persen
        FROM v_pems_comparison_division
        {where}
    """, params)
    return add_period_metadata(row) or {
        "jumlah_divisi": 0,
        "jumlah_estate": 0,
        "tanggal_laporan_anggaran": None,
        "tanggal_laporan_realisasi": None,
        "total_anggaran_ton": 0,
        "total_realisasi_ton": 0,
        "selisih_ton": 0,
        "pencapaian_persen": None,
        "period_status": "incomplete",
        "period_warning": "Belum ada data budget dan realisasi untuk dibandingkan.",
    }


@app.get("/api/estates")
def estates(
    estate_code: str | None = Query(default=None, max_length=10),
    division_code: str | None = Query(default=None, max_length=20),
):
    filters = []
    params = []
    if estate_code:
        filters.append("estate_code = %s")
        params.append(estate_code.upper())
    if division_code:
        filters.append("division_code = %s")
        params.append(division_code.upper())
    where = "WHERE " + " AND ".join(filters) if filters else ""
    rows = fetch_all(f"""
        SELECT
            estate_code,
            estate_name,
            COUNT(*)::INTEGER AS jumlah_divisi,
            MIN(budget_report_date) AS budget_report_date,
            MIN(actual_report_date) AS actual_report_date,
            SUM(budget_ton)::NUMERIC(14,4) AS anggaran_ton,
            SUM(actual_ton)::NUMERIC(14,4) AS realisasi_ton,
            SUM(variance_ton)::NUMERIC(14,4) AS selisih_ton,
            ROUND(
                100.0 * SUM(actual_ton) /
                NULLIF(SUM(budget_ton), 0),
                2
            ) AS pencapaian_persen
        FROM v_pems_comparison_division
        {where}
        GROUP BY estate_code, estate_name
        ORDER BY estate_code
    """, params)
    return {"count": len(rows), "items": add_period_metadata_many(rows)}


@app.get("/api/divisions")
def divisions(
    estate_code: str | None = Query(default=None, max_length=10),
    division_code: str | None = Query(default=None, max_length=20),
):
    sql = """
        SELECT
            estate_code,
            estate_name,
            division_code,
            division_number,
            budget_report_date,
            actual_report_date,
            budget_ton AS anggaran_ton,
            actual_ton AS realisasi_ton,
            variance_ton AS selisih_ton,
            achievement_pct AS pencapaian_persen
        FROM v_pems_comparison_division
    """

    filters = []
    params = []
    if estate_code:
        filters.append("estate_code = %s")
        params.append(estate_code.upper())
    if division_code:
        filters.append("division_code = %s")
        params.append(division_code.upper())
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY estate_code, division_number"
    rows = fetch_all(sql, params)

    return {"count": len(rows), "items": add_period_metadata_many(rows)}


from pathlib import Path
from fastapi.responses import FileResponse
from app.auth import (
    LoginRequest,
    login,
    logout,
    require_import_auth,
    require_session,
)


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    page = Path(__file__).parent / "static" / "index.html"
    if not page.is_file():
        raise HTTPException(
            status_code=404,
            detail="File dashboard belum ditemukan."
        )
    return FileResponse(page)


@app.post("/api/auth/login")
def auth_login(request: Request, response: Response, payload: LoginRequest):
    return login(request, response, payload)


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    return logout(request, response)


@app.get("/api/auth/me")
def auth_me(user=Depends(require_session)):
    return {"username": user["username"], "role": user["role"]}


# Endpoint impor didaftarkan langsung pada aplikasi utama
from app.import_routes import (
    import_preview,
    import_confirm,
)

app.add_api_route(
    "/api/import/preview",
    import_preview,
    methods=["POST"],
    tags=["Import Excel"],
    dependencies=[Depends(require_import_auth)],
)
app.add_api_route(
    "/api/import/confirm",
    import_confirm,
    methods=["POST"],
    tags=["Import Excel"],
    dependencies=[Depends(require_import_auth)],
)
