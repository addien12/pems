import time
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

import app.import_routes as mod


@pytest.fixture
def pending_import(monkeypatch, tmp_path):
    path = tmp_path / "confirm_error_probe.xlsx"
    path.write_bytes(b"isolated test data")

    token = "confirm-error-isolated-token"
    item = {
        "path": path,
        "kind": "budget",
        "filename": "confirm_error_probe.xlsx",
        "expires": time.monotonic() + 600,
    }

    with mod._lock:
        mod._pending[token] = item

    audit_calls = []
    monkeypatch.setattr(
        mod,
        "record_import_failure",
        lambda received_item, reason: audit_calls.append(
            (received_item, reason)
        ),
    )

    try:
        yield token, item, path, audit_calls
    finally:
        with mod._lock:
            mod._pending.pop(token, None)
            mod._processing_paths.discard(path)
            mod._uploading_paths.discard(path)
        path.unlink(missing_ok=True)


def test_duplicate_import_returns_409_and_records_failure(
    monkeypatch, pending_import
):
    token, item, path, audit_calls = pending_import

    def raise_duplicate(*args, **kwargs):
        raise psycopg.errors.UniqueViolation("duplicate probe")

    monkeypatch.setattr(mod, "save_import", raise_duplicate)

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 409
    assert audit_calls == [(item, "duplicate")]
    assert not path.exists()
    assert token not in mod._pending


def test_database_error_returns_503_and_records_failure(
    monkeypatch, pending_import
):
    token, item, path, audit_calls = pending_import

    def raise_database_error(*args, **kwargs):
        raise psycopg.OperationalError("database probe unavailable")

    monkeypatch.setattr(mod, "save_import", raise_database_error)

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 503
    assert audit_calls == [(item, "database_error")]
    assert not path.exists()
    assert token not in mod._pending


def test_audit_failure_does_not_mask_original_import_error(
    monkeypatch, pending_import
):
    token, item, path, audit_calls = pending_import

    def raise_database_error(*args, **kwargs):
        raise psycopg.OperationalError("original database probe error")

    def raise_audit_error(*args, **kwargs):
        audit_calls.append((args[0], args[1]))
        raise RuntimeError("audit probe error")

    monkeypatch.setattr(mod, "save_import", raise_database_error)
    monkeypatch.setattr(mod, "record_import_failure", raise_audit_error)

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 503
    assert audit_calls == [(item, "database_error")]
    assert not path.exists()
    assert token not in mod._pending
