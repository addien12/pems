import pytest
from fastapi.testclient import TestClient

import app.main as main


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PEMS_IMPORT_API_KEY", "test-import-api-key")
    return TestClient(main.app)


def test_preview_rejects_request_without_authentication(client):
    response = client.post(
        "/api/import/preview",
        data={"kind": "actual"},
        files={
            "file": (
                "sample.xlsx",
                b"not a real workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Login atau API key impor diperlukan."


def test_confirm_rejects_request_without_authentication(client):
    response = client.post(
        "/api/import/confirm",
        json={"token": "missing-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Login atau API key impor diperlukan."
