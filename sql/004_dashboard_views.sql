BEGIN;

-- =====================================================
-- VIEW 1: PERBANDINGAN ANGGARAN VS REALISASI PER DIVISI
-- Mengambil batch terbaru dari setiap sheet.
-- =====================================================

CREATE OR REPLACE VIEW v_pems_comparison_division AS
WITH latest_budget_batch AS (
    SELECT id, report_date
    FROM import_batches
    WHERE source_sheet = 'Budget Produksi'
    ORDER BY report_date DESC, id DESC
    LIMIT 1
),
latest_actual_batch AS (
    SELECT id, report_date
    FROM import_batches
    WHERE source_sheet = 'Produksi Tahun Ini'
    ORDER BY report_date DESC, id DESC
    LIMIT 1
),
budget AS (
    SELECT
        pb.division_id,
        SUM(pb.budget_ton) AS budget_ton
    FROM production_budgets pb
    JOIN latest_budget_batch lb
        ON lb.id = pb.import_batch_id
    GROUP BY pb.division_id
),
actual AS (
    SELECT
        pa.division_id,
        SUM(pa.actual_ton) AS actual_ton
    FROM production_actuals pa
    JOIN latest_actual_batch la
        ON la.id = pa.import_batch_id
    GROUP BY pa.division_id
)
SELECT
    lb.report_date AS budget_report_date,
    la.report_date AS actual_report_date,
    e.code AS estate_code,
    e.name AS estate_name,
    d.code AS division_code,
    d.division_number,
    COALESCE(b.budget_ton, 0)::NUMERIC(14,4) AS budget_ton,
    COALESCE(a.actual_ton, 0)::NUMERIC(14,4) AS actual_ton,
    (
        COALESCE(a.actual_ton, 0) -
        COALESCE(b.budget_ton, 0)
    )::NUMERIC(14,4) AS variance_ton,
    ROUND(
        100.0 * COALESCE(a.actual_ton, 0) /
        NULLIF(b.budget_ton, 0),
        2
    ) AS achievement_pct
FROM divisions d
JOIN estates e
    ON e.id = d.estate_id
    LEFT JOIN latest_budget_batch lb
        ON TRUE
    LEFT JOIN latest_actual_batch la
        ON TRUE
LEFT JOIN budget b
    ON b.division_id = d.id
LEFT JOIN actual a
    ON a.division_id = d.id
WHERE d.is_active = TRUE
  AND e.is_active = TRUE;


-- =====================================================
-- VIEW 2: REKAP ANGGARAN VS REALISASI PER ESTATE
-- =====================================================

CREATE OR REPLACE VIEW v_pems_comparison_estate AS
SELECT
    budget_report_date,
    actual_report_date,
    estate_code,
    estate_name,
    COUNT(*) AS jumlah_divisi,
    SUM(budget_ton)::NUMERIC(14,4) AS budget_ton,
    SUM(actual_ton)::NUMERIC(14,4) AS actual_ton,
    SUM(variance_ton)::NUMERIC(14,4) AS variance_ton,
    ROUND(
        100.0 * SUM(actual_ton) /
        NULLIF(SUM(budget_ton), 0),
        2
    ) AS achievement_pct
FROM v_pems_comparison_division
GROUP BY
    budget_report_date,
    actual_report_date,
    estate_code,
    estate_name;

COMMIT;
