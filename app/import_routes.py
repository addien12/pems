import os
import json
import logging
import zipfile
import time
import secrets
import threading
from pathlib import Path

import psycopg
from openpyxl.utils.exceptions import InvalidFileException
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from app.import_service import validate_workbook, save_import

router = APIRouter(prefix="/api/import", tags=["Import Excel"])

STAGING = Path(__file__).resolve().parent.parent / "imports" / "staging"
MAX_UPLOAD = 20 * 1024 * 1024
TOKEN_TTL = 10 * 60
IMPORT_API_KEY_ENV = "PEMS_IMPORT_API_KEY"

_pending = {}
_processing_paths = set()
_lock = threading.Lock()
logger = logging.getLogger(__name__)


class ConfirmRequest(BaseModel):
    token: str


def require_import_api_key(
    x_pems_import_key: str | None = Header(default=None),
):
    """Lindungi endpoint mutasi impor tanpa menyimpan kredensial di Git."""
    expected = os.getenv(IMPORT_API_KEY_ENV)
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=f"{IMPORT_API_KEY_ENV} belum dikonfigurasi.",
        )
    if not x_pems_import_key or not secrets.compare_digest(
        x_pems_import_key, expected
    ):
        raise HTTPException(
            status_code=401,
            detail="API key impor tidak valid.",
        )


def cleanup_expired():
    now = time.monotonic()
    expired = []

    with _lock:
        for token, item in list(_pending.items()):
            if item["expires"] <= now:
                expired.append(_pending.pop(token))

    for item in expired:
        try:
            item["path"].unlink(missing_ok=True)
        except OSError:
            pass

    cleanup_orphaned_staging_files()

def cleanup_orphaned_staging_files():
    """Hapus file XLSX yatim yang lebih tua dari 30 menit."""
    cutoff = time.time() - 30 * 60

    with _lock:
        active_paths = {
            item["path"].resolve()
            for item in _pending.values()
        }
        active_paths.update(path.resolve() for path in _processing_paths)

    try:
        for path in STAGING.glob("*.xlsx"):
            try:
                resolved = path.resolve()
                if resolved in active_paths:
                    continue
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Tidak dapat membersihkan file staging: %s",
                    path.name,
                )
    except OSError:
        logger.exception("Gagal memeriksa direktori staging.")


def record_import_failure(item, reason):
    """Catat kegagalan impor setelah transaksi impor dibatalkan."""
    try:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql:///pems_db"
        )
        details = {
            "status": "failed",
            "kind": item.get("kind"),
            "filename": item.get("filename"),
            "reason": reason,
        }

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_logs
                        (actor, action, entity_type, entity_id, details)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        "web-user",
                        "IMPORT_FAILED",
                        "import_attempt",
                        item.get("filename", "unknown"),
                        json.dumps(details),
                    ),
                )
    except Exception:
        # Jangan sampai kegagalan audit menutupi error impor asli.
        logger.exception("Gagal mencatat audit kegagalan impor.")


@router.post("/preview")
def import_preview(
    kind: str = Form(...),
    file: UploadFile = File(...),
):
    cleanup_expired()

    if kind not in ("budget", "actual"):
        raise HTTPException(
            status_code=400,
            detail="Jenis impor harus budget atau actual.",
        )

    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Format file harus .xlsx.",
        )

    STAGING.mkdir(parents=True, exist_ok=True)
    temp_path = STAGING / f"{secrets.token_hex(16)}.xlsx"
    size = 0

    try:
        with temp_path.open("xb") as destination:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break

                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(
                        status_code=413,
                        detail="Ukuran file maksimal 20 MB.",
                    )

                destination.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="File yang diunggah kosong.",
            )

        try:
                preview = validate_workbook(temp_path, kind)
        except (zipfile.BadZipFile, InvalidFileException) as exc:
            raise HTTPException(
                status_code=422,
                detail="File bukan workbook Excel .xlsx yang valid atau file rusak.",
            ) from exc
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Validasi workbook gagal: {exc}",
            ) from exc

        token = secrets.token_urlsafe(32)

        with _lock:
            _pending[token] = {
                "path": temp_path,
                "kind": kind,
                "filename": filename,
                "expires": time.monotonic() + TOKEN_TTL,
            }

        return {
            "status": "valid",
            "message": "Validasi berhasil. Periksa pratinjau sebelum konfirmasi.",
            "token": token,
            "expires_in_seconds": TOKEN_TTL,
            "kind": kind,
            "filename": filename,
            "sheet": preview["sheet"],
            "report_date": preview["report_date"],
            "division_count": preview["division_count"],
            "record_count": preview["record_count"],
            "total_ton": preview["total_ton"],
        }

    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Gagal memproses file sementara.",
        ) from exc
    finally:
        file.file.close()


@router.post("/confirm")
def import_confirm(payload: ConfirmRequest):
    cleanup_expired()

    with _lock:
        item = _pending.pop(payload.token, None)
        if item is not None:
            _processing_paths.add(item["path"])

    if item is None:
        raise HTTPException(
            status_code=410,
            detail="Token tidak ditemukan, sudah digunakan, atau kedaluwarsa. Unggah ulang file.",
        )

    path = item["path"]

    try:
        if time.monotonic() >= item["expires"]:
            raise HTTPException(
                status_code=410,
                detail="Pratinjau sudah kedaluwarsa. Unggah ulang file.",
            )

        result = save_import(
            path,
            item["kind"],
            actor="web-user",
            source_filename=item["filename"],
        )

        return {
            "status": "success",
            "message": "Impor berhasil disimpan ke database.",
            **result,
        }

    except ValueError as exc:
        message = str(exc)
        if "sudah diimpor" in message.lower():
            record_import_failure(item, "duplicate")
        else:
            record_import_failure(item, "validation_or_conflict")
        raise HTTPException(status_code=409, detail=message) from exc
    except psycopg.errors.UniqueViolation as exc:
        record_import_failure(item, "duplicate")
        raise HTTPException(
            status_code=409,
            detail="Impor duplikat terdeteksi oleh database.",
        ) from exc
    except psycopg.Error as exc:
        record_import_failure(item, "database_error")
        raise HTTPException(
            status_code=503,
            detail="Database gagal menyimpan impor. Silakan periksa status database.",
        ) from exc
    except Exception as exc:
        record_import_failure(item, "unexpected_error")
        raise HTTPException(
            status_code=500,
            detail="Impor gagal diproses. Silakan periksa status sistem.",
        ) from exc
    finally:
        with _lock:
            _processing_paths.discard(path)
        path.unlink(missing_ok=True)
