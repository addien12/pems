import os
import sys
from pathlib import Path

import pytest
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_import_transaction_rollback():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        pytest.skip("DATABASE_URL belum diatur.")

    from urllib.parse import urlparse
    db_name = urlparse(database_url).path.lstrip("/")

    if db_name != "pems_test_import":
        pytest.skip(
            "Tes rollback hanya boleh berjalan pada pems_test_import."
        )

    with psycopg.connect(database_url) as conn:
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

        with pytest.raises(psycopg.Error):
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

                    cur.execute("""
                        INSERT INTO production_budgets
                            (import_batch_id, division_id, budget_date,
                             budget_ton, source_row)
                        VALUES (%s, -999999999, CURRENT_DATE, 1, 999999)
                    """, (batch_id,))

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
