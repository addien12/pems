BEGIN;

CREATE TABLE IF NOT EXISTS estates (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS divisions (
    id BIGSERIAL PRIMARY KEY,
    estate_id BIGINT NOT NULL REFERENCES estates(id),
    code VARCHAR(20) NOT NULL UNIQUE,
    division_number SMALLINT NOT NULL CHECK (division_number > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, division_number)
);

CREATE TABLE IF NOT EXISTS import_batches (
    id BIGSERIAL PRIMARY KEY,
    source_filename TEXT NOT NULL,
    source_sha256 CHAR(64) NOT NULL,
    source_sheet VARCHAR(100) NOT NULL,
    report_date DATE NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    imported_by TEXT NOT NULL DEFAULT 'termux-cli',
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_import_batches_sha256
    ON import_batches(source_sha256);
CREATE UNIQUE INDEX IF NOT EXISTS uq_import_batches_hash_sheet
    ON import_batches(source_sha256, source_sheet);

CREATE TABLE IF NOT EXISTS production_budgets (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id BIGINT NOT NULL REFERENCES import_batches(id),
    division_id BIGINT NOT NULL REFERENCES divisions(id),
    budget_date DATE NOT NULL,
    budget_ton NUMERIC(14,4) NOT NULL CHECK (budget_ton >= 0),
    source_row INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (import_batch_id, division_id, budget_date)
);
CREATE INDEX IF NOT EXISTS idx_production_budgets_date
    ON production_budgets(budget_date);
CREATE INDEX IF NOT EXISTS idx_production_budgets_division_date
    ON production_budgets(division_id, budget_date);

CREATE TABLE IF NOT EXISTS production_actuals (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id BIGINT NOT NULL REFERENCES import_batches(id),
    division_id BIGINT NOT NULL REFERENCES divisions(id),
    actual_date DATE NOT NULL,
    actual_ton NUMERIC(14,4) NOT NULL CHECK (actual_ton >= 0),
    source_row INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (import_batch_id, division_id, actual_date)
);
CREATE INDEX IF NOT EXISTS idx_production_actuals_date
    ON production_actuals(actual_date);
CREATE INDEX IF NOT EXISTS idx_production_actuals_division_date
    ON production_actuals(division_id, actual_date);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor TEXT NOT NULL DEFAULT 'system',
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
