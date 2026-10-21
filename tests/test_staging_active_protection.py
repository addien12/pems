import os
import sys
import time
import tempfile
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
mod = importlib.import_module("app.import_routes")
mod.STAGING.mkdir(parents=True, exist_ok=True)

def make_old_probe():
    fd, name = tempfile.mkstemp(
        prefix="cleanup_active_probe_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)
    path = Path(name)
    old = time.time() - 31 * 60
    os.utime(path, (old, old))
    return path

pending_probe = make_old_probe()
processing_probe = make_old_probe()
unprotected_probe = make_old_probe()

try:
    with mod._lock:
        mod._pending["test-active-token"] = {
            "path": pending_probe,
            "kind": "budget",
            "filename": "test.xlsx",
            "expires": time.monotonic() + 600,
        }
        mod._processing_paths.add(processing_probe)

    mod.cleanup_orphaned_staging_files()

    assert pending_probe.exists(), "File preview aktif ikut terhapus."
    assert processing_probe.exists(), "File yang diproses ikut terhapus."
    assert not unprotected_probe.exists(), "File yatim tua tidak dibersihkan."

    print("LULUS: preview aktif dipertahankan.")
    print("LULUS: file yang diproses dipertahankan.")
    print("LULUS: file yatim tua dibersihkan.")

finally:
    with mod._lock:
        mod._pending.pop("test-active-token", None)
        mod._processing_paths.discard(processing_probe)
    for path in (pending_probe, processing_probe, unprotected_probe):
        path.unlink(missing_ok=True)
