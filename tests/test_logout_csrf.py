import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.auth as auth
import app.main as main


class _Cursor:
    def execute(self, *args):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def cursor(self):
        return _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_logout_rejects_active_session_without_csrf(monkeypatch):
    user = {"id": 7, "username": "admin_utama", "role": "admin_utama"}
    monkeypatch.setattr(auth, "get_session_user", lambda request: user)

    def reject_csrf(request, current_user):
        raise HTTPException(403, "Token CSRF tidak valid.")

    monkeypatch.setattr(auth, "require_csrf", reject_csrf)
    client = TestClient(main.app)

    response = client.post(
        "/api/auth/logout",
        cookies={auth.SESSION_COOKIE: "session-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Token CSRF tidak valid."


def test_logout_accepts_active_session_with_valid_csrf(monkeypatch):
    user = {"id": 7, "username": "admin_utama", "role": "admin_utama"}
    monkeypatch.setattr(auth, "get_session_user", lambda request: user)
    monkeypatch.setattr(auth, "require_csrf", lambda request, current_user: None)
    monkeypatch.setattr(auth, "_connect", lambda: _Connection())
    client = TestClient(main.app)

    response = client.post(
        "/api/auth/logout",
        cookies={
            auth.SESSION_COOKIE: "session-token",
            auth.CSRF_COOKIE: "csrf-token",
        },
        headers={"X-PEMS-CSRF": "csrf-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert any(
        auth.SESSION_COOKIE in value and "Max-Age=0" in value
        for value in response.headers.get_list("set-cookie")
    )


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_logout_route_remains_post_only(method):
    client = TestClient(main.app)
    response = getattr(client, method)("/api/auth/logout")
    assert response.status_code == 405
