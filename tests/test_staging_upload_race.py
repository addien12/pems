import os
import tempfile
import time
from pathlib import Path

import app.import_routes as mod


def make_old_probe():
    fd, name = tempfile.mkstemp(
        prefix="cleanup_uploading_probe_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)
    path = Path(name)
    old = time.time() - 31 * 60
    os.utime(path, (old, old))
    return path


def test_staging_cleanup_preserves_active_upload():
    mod.STAGING.mkdir(parents=True, exist_ok=True)
    uploading_probe = make_old_probe()

    try:
        with mod._lock:
            mod._uploading_paths.add(uploading_probe)

        mod.cleanup_orphaned_staging_files()

        assert uploading_probe.exists(), (
            "File yang sedang diunggah ikut terhapus."
        )
    finally:
        with mod._lock:
            mod._uploading_paths.discard(uploading_probe)
        uploading_probe.unlink(missing_ok=True)


def test_expired_preview_is_removed_and_file_cleaned():
    mod.STAGING.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(
        prefix="expired_preview_probe_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)
    path = Path(name)
    token = "expired-preview-token"

    try:
        with mod._lock:
            mod._pending[token] = {
                "path": path,
                "kind": "budget",
                "filename": "expired.xlsx",
                "expires": time.monotonic() - 1,
            }

        mod.cleanup_expired()

        with mod._lock:
            assert token not in mod._pending
        assert not path.exists()
    finally:
        with mod._lock:
            mod._pending.pop(token, None)
            mod._uploading_paths.discard(path)
            mod._processing_paths.discard(path)
        path.unlink(missing_ok=True)

def test_cleanup_removes_old_upload_after_active_state_is_released():
    mod.STAGING.mkdir(parents=True, exist_ok=True)
    path = make_old_probe()

    try:
        with mod._lock:
            mod._uploading_paths.add(path)

        mod.cleanup_orphaned_staging_files()
        assert path.exists(), "File upload aktif tidak boleh dihapus."

        with mod._lock:
            mod._uploading_paths.discard(path)

        mod.cleanup_orphaned_staging_files()
        assert not path.exists(), (
            "File lama harus dibersihkan setelah status upload aktif dilepas."
        )
    finally:
        with mod._lock:
            mod._uploading_paths.discard(path)
            mod._processing_paths.discard(path)
        path.unlink(missing_ok=True)
