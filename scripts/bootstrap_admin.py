"""Buat Admin Utama sekali melalui environment variable yang aman."""
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import DATABASE_URL, hash_password


def main():
    username = os.getenv("PEMS_ADMIN_USERNAME", "").strip()
    password = os.getenv("PEMS_ADMIN_PASSWORD", "")
    if not username or not password:
        raise SystemExit(
            "PEMS_ADMIN_USERNAME dan PEMS_ADMIN_PASSWORD wajib diatur "
            "untuk bootstrap; nilai tidak ditampilkan."
        )
    if len(username) > 100 or len(password) < 12:
        raise SystemExit("Username maksimal 100 karakter dan password minimal 12 karakter.")
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM auth_users WHERE username = %s", (username,))
            if cursor.fetchone():
                print("Admin sudah ada; tidak ada perubahan.")
                return
            cursor.execute(
                "INSERT INTO auth_users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, hash_password(password), "admin_utama"),
            )
    print("Admin berhasil dibuat.")


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error as exc:
        sys.exit(f"Bootstrap dibatalkan: database tidak dapat diakses ({exc.__class__.__name__}).")
