import os
from contextlib import closing

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query

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


@app.get("/api/summary")
def summary():
    return fetch_one("""
        SELECT
            COUNT(*)::INTEGER AS jumlah_divisi,
            COUNT(DISTINCT estate_code)::INTEGER AS jumlah_estate,
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
    """)


@app.get("/api/estates")
def estates():
    rows = fetch_all("""
        SELECT
            estate_code,
            estate_name,
            jumlah_divisi,
            budget_report_date,
            actual_report_date,
            budget_ton AS anggaran_ton,
            actual_ton AS realisasi_ton,
            variance_ton AS selisih_ton,
            achievement_pct AS pencapaian_persen
        FROM v_pems_comparison_estate
        ORDER BY estate_code
    """)
    return {"count": len(rows), "items": rows}


@app.get("/api/divisions")
def divisions(
    estate_code: str | None = Query(default=None, max_length=10),
):
    code = estate_code.upper() if estate_code else None

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

    if code:
        sql += """
            WHERE estate_code = %s
            ORDER BY estate_code, division_number
        """
        rows = fetch_all(sql, (code,))
    else:
        sql += " ORDER BY estate_code, division_number"
        rows = fetch_all(sql)

    return {"count": len(rows), "items": rows}


from pathlib import Path
from fastapi.responses import FileResponse


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    page = Path(__file__).parent / "static" / "index.html"
    if not page.is_file():
        raise HTTPException(
            status_code=404,
            detail="File dashboard belum ditemukan."
        )
    return FileResponse(page)


# Endpoint impor didaftarkan langsung pada aplikasi utama
from app.import_routes import import_preview, import_confirm

app.add_api_route(
    "/api/import/preview",
    import_preview,
    methods=["POST"],
    tags=["Import Excel"],
)
app.add_api_route(
    "/api/import/confirm",
    import_confirm,
    methods=["POST"],
    tags=["Import Excel"],
)
