import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "")

if "pems_test_import" not in DATABASE_URL:
    raise SystemExit(
        "STOP: DATABASE_URL harus menunjuk ke pems_test_import."
    )

conn = psycopg.connect(DATABASE_URL)

try:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM import_batches")
        batches_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM audit_logs")
        audits_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM production_budgets")
        budgets_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM production_actuals")
        actuals_before = cur.fetchone()[0]

    conn.commit()

    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO import_batches
                        (source_filename, source_sha256, source_sheet,
                         report_date, imported_by, notes)
                    VALUES (
                        'ROLLBACK_PROBE_ONLY.xlsx',
                        repeat('a', 64),
                        'Rollback Probe',
                        CURRENT_DATE,
                        'rollback-test',
                        'Transaksi uji; harus di-rollback'
                    )
                    RETURNING id
                """)
                batch_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO audit_logs
                        (actor, action, entity_type, entity_id, details)
                    VALUES (
                        'rollback-test',
                        'ROLLBACK_PROBE',
                        'import_batch',
                        %s,
                        '{}'::jsonb
                    )
                """, (str(batch_id),))

                # Sengaja memicu pelanggaran FK.
                cur.execute("""
                    INSERT INTO production_budgets
                        (import_batch_id, division_id, budget_date,
                         budget_ton, source_row)
                    VALUES (%s, -999999999, CURRENT_DATE, 1, 999999)
                """, (batch_id,))

    except psycopg.Error:
        pass
    else:
        raise AssertionError("Kegagalan yang diharapkan tidak terjadi.")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM import_batches "
            "WHERE source_filename = 'ROLLBACK_PROBE_ONLY.xlsx'"
        )
        probe_batches = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE action = 'ROLLBACK_PROBE' "
            "AND actor = 'rollback-test'"
        )
        probe_audits = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM import_batches")
        batches_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM audit_logs")
        audits_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM production_budgets")
        budgets_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM production_actuals")
        actuals_after = cur.fetchone()[0]

    assert probe_batches == 0, "Batch uji tertinggal setelah rollback."
    assert probe_audits == 0, "Audit uji tertinggal setelah rollback."
    assert batches_after == batches_before, "Jumlah batch berubah."
    assert audits_after == audits_before, "Jumlah audit berubah."
    assert budgets_after == budgets_before, "Jumlah anggaran berubah."
    assert actuals_after == actuals_before, "Jumlah aktual berubah."

    print("LULUS: kegagalan transaksi berhasil memicu rollback.")
    print("LULUS: batch dan audit uji tidak tertinggal.")
    print("LULUS: jumlah batch, anggaran, aktual, dan audit tetap.")

finally:
    conn.close()
