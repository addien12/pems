import pytest
from starlette.requests import Request
from starlette.responses import Response

import app.auth as auth


def request(headers=None, cookies=None):
    headers = dict(headers or {})
    if cookies:
        headers["cookie"] = "; ".join(f"{key}={value}" for key, value in cookies.items())
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
        "client": ("127.0.0.1", 1234),
        "scheme": "https",
        "query_string": b"",
        "server": ("testserver", 443),
    }
    result = Request(scope)
    return result


def test_password_hash_is_not_plaintext_and_verifies():
    encoded = auth.hash_password("A-strong-test-password-123")
    assert encoded != "A-strong-test-password-123"
    assert encoded.startswith("scrypt$")
    assert auth.verify_password("A-strong-test-password-123", encoded)
    assert not auth.verify_password("wrong-password", encoded)


def test_import_auth_accepts_legacy_api_key(monkeypatch):
    monkeypatch.setenv("PEMS_IMPORT_API_KEY", "legacy-secret")
    result = auth.require_import_auth(
        request(headers={"x-pems-import-key": "legacy-secret"})
    )
    assert result["username"] == "legacy-api-key"
    assert result["role"] == "admin_utama"


def test_import_auth_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("PEMS_IMPORT_API_KEY", raising=False)
    with pytest.raises(Exception) as error:
        auth.require_import_auth(request())
    assert error.value.status_code == 503


def test_import_auth_requires_csrf_for_session(monkeypatch):
    user = {"id": 7, "username": "admin_utama", "role": "admin_utama"}
    monkeypatch.setattr(auth, "get_session_user", lambda request: user)
    monkeypatch.setattr(
        auth,
        "require_csrf",
        lambda request, current_user: (_ for _ in ()).throw(
            auth.HTTPException(403, "Token CSRF tidak valid.")
        ),
    )
    with pytest.raises(auth.HTTPException) as error:
        auth.require_import_auth(request(cookies={auth.SESSION_COOKIE: "token"}))
    assert error.value.status_code == 403


def test_role_check_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_session_user",
        lambda request: {"id": 8, "username": "viewer", "role": "viewer"},
    )
    with pytest.raises(auth.HTTPException) as error:
        auth.require_admin(request())
    assert error.value.status_code == 403


def test_expired_session_is_not_accepted_by_query(monkeypatch):
    class Cursor:
        def execute(self, *args):
            return None

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(auth, "_connect", lambda: Connection())
    assert auth.get_session_user(request(cookies={auth.SESSION_COOKIE: "expired"})) is None


def test_login_response_sets_secure_session_and_csrf_cookies(monkeypatch):
    class Cursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchone(self):
            return (3, "admin_utama", auth.hash_password("correct-password"), "admin_utama")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(auth, "_connect", lambda: Connection())
    response = Response()
    result = auth.login(
        request(), response, auth.LoginRequest(username="admin_utama", password="correct-password")
    )
    assert result == {"status": "ok", "username": "admin_utama", "role": "admin_utama"}
    cookies = response.headers.getlist("set-cookie")
    assert any(auth.SESSION_COOKIE in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any(auth.CSRF_COOKIE in cookie and "HttpOnly" not in cookie for cookie in cookies)
