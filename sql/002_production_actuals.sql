BEGIN;

-- Satu file dapat memiliki beberapa sheet yang diimpor terpisah.
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_import_batches_hash_sheet
ON import_batches (source_sha256, source_sheet);

-- Realisasi produksi dipisahkan dari tabel budget.
CREATE TABLE IF NOT EXISTS production_actuals (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id BIGINT NOT NULL
        REFERENCES import_batches(id),
    division_id BIGINT NOT NULL
        REFERENCES divisions(id),
    actual_date DATE NOT NULL,
    actual_ton NUMERIC(14,4) NOT NULL
        CHECK (actual_ton >= 0),
    source_row INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (import_batch_id, division_id, actual_date)
);

CREATE INDEX IF NOT EXISTS idx_actuals_date
    ON production_actuals(actual_date);

CREATE INDEX IF NOT EXISTS idx_actuals_division_date
    ON production_actuals(division_id, actual_date);

COMMIT;
