import time
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

import app.import_routes as mod


@pytest.fixture
def pending_import(tmp_path):
    path = Path(tmp_path) / "import-failure.xlsx"
    path.write_bytes(b"staged")
    token = f"failure-test-{time.monotonic_ns()}"
    item = {
        "path": path,
        "kind": "actual",
        "filename": "import-failure.xlsx",
        "expires": time.monotonic() + 600,
    }
    with mod._lock:
        mod._pending[token] = item
    try:
        yield token, item
    finally:
        with mod._lock:
            mod._pending.pop(token, None)
            mod._processing_paths.discard(path)
        path.unlink(missing_ok=True)


def test_duplicate_returns_409_audits_and_cleans_staging(
    monkeypatch, pending_import
):
    token, item = pending_import
    audit_reasons = []
    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("batch sudah diimpor")
        ),
    )
    monkeypatch.setattr(
        mod,
        "record_import_failure",
        lambda received, reason: audit_reasons.append((received, reason)),
    )

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 409
    assert audit_reasons == [(item, "duplicate")]
    assert not item["path"].exists()


def test_database_error_returns_503_audits_and_cleans_staging(
    monkeypatch, pending_import
):
    token, item = pending_import
    audit_reasons = []
    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            psycopg.Error("database unavailable")
        ),
    )
    monkeypatch.setattr(
        mod,
        "record_import_failure",
        lambda received, reason: audit_reasons.append((received, reason)),
    )

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 503
    assert audit_reasons == [(item, "database_error")]
    assert not item["path"].exists()


def test_audit_failure_does_not_mask_duplicate_error(
    monkeypatch, pending_import
):
    token, item = pending_import
    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("batch sudah diimpor")
        ),
    )

    def failing_audit(*args, **kwargs):
        raise RuntimeError("audit service unavailable")

    monkeypatch.setattr(mod, "record_import_failure", failing_audit)

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 409
    assert "sudah diimpor" in exc_info.value.detail
    assert not item["path"].exists()
