import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///pems_db")
SESSION_COOKIE = "pems_session"
CSRF_COOKIE = "pems_csrf"
SESSION_TTL_SECONDS = int(os.getenv("PEMS_SESSION_TTL_SECONDS", str(8 * 60 * 60)))
COOKIE_SECURE = os.getenv("PEMS_COOKIE_SECURE", "false").lower() == "true"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
_attempts = {}
_attempts_lock = threading.Lock()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


def _b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password):
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password, encoded):
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(_b64(derived), expected)
    except (ValueError, TypeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _client_key(request):
    return request.client.host if request.client else "unknown"


def _rate_limited(key):
    now = time.monotonic()
    with _attempts_lock:
        attempts = [stamp for stamp in _attempts.get(key, [])
                    if stamp > now - LOGIN_WINDOW_SECONDS]
        _attempts[key] = attempts
        return len(attempts) >= MAX_LOGIN_ATTEMPTS


def _record_failed_attempt(key):
    with _attempts_lock:
        _attempts.setdefault(key, []).append(time.monotonic())


def _clear_attempts(key):
    with _attempts_lock:
        _attempts.pop(key, None)


def _connect():
    return psycopg.connect(DATABASE_URL)


def get_session_user(request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.id, u.username, u.role
                    FROM auth_sessions s
                    JOIN auth_users u ON u.id = s.user_id
                    WHERE s.token_hash = %s
                      AND s.expires_at > NOW()
                      AND u.is_active = TRUE
                    """,
                    (hash_token(token),),
                )
                row = cursor.fetchone()
                return dict(zip(("id", "username", "role"), row)) if row else None
    except psycopg.Error as exc:
        raise HTTPException(503, "Database PEMS tidak dapat diakses.") from exc


def require_session(request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(401, "Login diperlukan.")
    return user


def require_admin(request):
    user = require_session(request)
    if user["role"] != "admin_utama":
        raise HTTPException(403, "Akses tidak diizinkan.")
    return user


def require_csrf(request, user):
    token = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("X-PEMS-CSRF")
    if not token or not header or not hmac.compare_digest(token, header):
        raise HTTPException(403, "Token CSRF tidak valid.")
    session_token = request.cookies.get(SESSION_COOKIE)
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM auth_sessions WHERE user_id = %s AND token_hash = %s AND csrf_hash = %s AND expires_at > NOW()",
                (user["id"], hash_token(session_token), hash_token(token)),
            )
            if not cursor.fetchone():
                raise HTTPException(403, "Token CSRF tidak valid.")


def require_import_auth(request):
    user = get_session_user(request)
    if user:
        require_csrf(request, user)
        return user
    expected = os.getenv("PEMS_IMPORT_API_KEY")
    provided = request.headers.get("X-PEMS-Import-Key")
    if expected and provided and hmac.compare_digest(provided, expected):
        return {"id": None, "username": "legacy-api-key", "role": "admin_utama"}
    if not expected:
        raise HTTPException(503, "Autentikasi impor belum dikonfigurasi.")
    raise HTTPException(401, "Login atau API key impor diperlukan.")


def login(request, response, payload):
    key = _client_key(request)
    if _rate_limited(key):
        raise HTTPException(429, "Terlalu banyak percobaan login. Coba lagi nanti.")
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, password_hash, role FROM auth_users WHERE username = %s AND is_active = TRUE",
                    (payload.username.strip(),),
                )
                row = cursor.fetchone()
                if not row or not verify_password(payload.password, row[2]):
                    _record_failed_attempt(key)
                    raise HTTPException(401, "Username atau password tidak valid.")
                token = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                expires = _now() + timedelta(seconds=SESSION_TTL_SECONDS)
                cursor.execute(
                    "INSERT INTO auth_sessions (user_id, token_hash, csrf_hash, expires_at) VALUES (%s, %s, %s, %s)",
                    (row[0], hash_token(token), hash_token(csrf), expires),
                )
        _clear_attempts(key)
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(503, "Database PEMS tidak dapat diakses.") from exc
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_TTL_SECONDS,
                        httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=SESSION_TTL_SECONDS,
                        httponly=False, secure=COOKIE_SECURE, samesite="lax", path="/")
    return {"status": "ok", "username": row[1], "role": row[3]}


def logout(request, response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            with _connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (hash_token(token),))
        except psycopg.Error as exc:
            raise HTTPException(503, "Database PEMS tidak dapat diakses.") from exc
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "ok"}


def cleanup_sessions():
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_sessions WHERE expires_at <= NOW()")
