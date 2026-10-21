import pytest
from fastapi import HTTPException

from app.import_routes import require_import_api_key


def test_import_api_key_is_required(monkeypatch):
    monkeypatch.delenv("PEMS_IMPORT_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_import_api_key(None)

    assert exc_info.value.status_code == 503


def test_import_api_key_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("PEMS_IMPORT_API_KEY", "expected-secret")

    with pytest.raises(HTTPException) as exc_info:
        require_import_api_key("wrong-secret")

    assert exc_info.value.status_code == 401


def test_import_api_key_accepts_matching_value(monkeypatch):
    monkeypatch.setenv("PEMS_IMPORT_API_KEY", "expected-secret")

    assert require_import_api_key("expected-secret") is None
