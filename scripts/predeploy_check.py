"""Read-only production readiness checks for PEMS deployment."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "sql/schema.sql",
    "sql/005_authentication.sql",
    "sql/003_reference_data.sql",
    "sql/004_dashboard_views.sql",
)
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _check_database_url(environment: str) -> tuple[str, str | None]:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        return "error", "DATABASE_URL belum dikonfigurasi."
    parsed = urlparse(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return "error", "DATABASE_URL harus menggunakan skema PostgreSQL."
    if environment == "production" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        return "error", "DATABASE_URL production tidak boleh menunjuk localhost."
    return "ok", None


def _check_cookie_secure(environment: str) -> tuple[str, str | None]:
    raw = os.getenv("PEMS_COOKIE_SECURE", "").strip().lower()
    if raw not in TRUE_VALUES | FALSE_VALUES:
        return "error", "PEMS_COOKIE_SECURE harus berupa true/false."
    if environment == "production" and raw not in TRUE_VALUES:
        return "error", "PEMS_COOKIE_SECURE harus true pada production HTTPS."
    return "ok", None


def run_checks(environment: str | None = None) -> list[tuple[str, str, str | None]]:
    target = (environment or os.getenv("PEMS_ENV", "local")).strip().lower()
    if target not in {"local", "test", "production"}:
        return [("environment", "error", "PEMS_ENV harus local, test, atau production.")]

    results = [
        ("environment", "ok", target),
        ("database_url", *_check_database_url(target)),
        ("cookie_secure", *_check_cookie_secure(target)),
    ]
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        results.append(
            (
                relative,
                "ok" if path.is_file() else "error",
                None if path.is_file() else "File deployment wajib tidak ditemukan.",
            )
        )
    return results


def main() -> int:
    results = run_checks()
    failed = False
    for name, status, detail in results:
        print(f"[{status.upper()}] {name}")
        if detail and name != "environment":
            print(f"  {detail}")
        failed |= status == "error"
    if failed:
        print("Readiness check gagal; deployment belum direkomendasikan.")
        return 1
    print("Readiness check lulus; pemeriksaan ini tidak menguji koneksi atau menulis database.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
