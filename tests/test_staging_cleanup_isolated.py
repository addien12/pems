import os
import sys
import time
import tempfile
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
mod = importlib.import_module("app.import_routes")
mod.STAGING.mkdir(parents=True, exist_ok=True)


def test_staging_cleanup_removes_old_files_and_keeps_new_files():
    fd, name = tempfile.mkstemp(
        prefix="cleanup_probe_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)
    probe = Path(name)

    try:
        old_time = time.time() - 31 * 60
        os.utime(probe, (old_time, old_time))

        mod.cleanup_orphaned_staging_files()

        assert not probe.exists(), (
            "File dummy tua tidak dibersihkan."
        )

        probe.touch()
        mod.cleanup_orphaned_staging_files()

        assert probe.exists(), (
            "File dummy baru ikut terhapus."
        )

    finally:
        probe.unlink(missing_ok=True)
