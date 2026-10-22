import os
import tempfile
import threading
import time
from pathlib import Path

import app.import_routes as mod


def test_cleanup_can_overlap_processing_release_before_unlink(monkeypatch):
    """Reproduce cleanup between processing release and final unlink safely."""
    mod.STAGING.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(
        prefix="cleanup_thread_race_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)
    path = Path(filename)
    old = time.time() - 31 * 60
    os.utime(path, (old, old))

    token = "cleanup-thread-race-token"
    discard_seen = threading.Event()
    cleanup_done = threading.Event()
    cleanup_errors = []
    original_processing_paths = mod._processing_paths
    original_unlink = type(path).unlink

    class ProcessingSet(set):
        def discard(self, value):
            super().discard(value)
            if value == path:
                discard_seen.set()

    def run_cleanup():
        try:
            if not discard_seen.wait(timeout=2):
                raise AssertionError("processing path tidak pernah dilepas")
            mod.cleanup_orphaned_staging_files()
        except BaseException as exc:  # propagate assertion from worker thread
            cleanup_errors.append(exc)
        finally:
            cleanup_done.set()

    def coordinated_unlink(self, missing_ok=False):
        # Force the confirm thread to observe cleanup deleting the now-inactive
        # path first. Both operations must remain safe with missing_ok=True.
        if (
            self.resolve() == path.resolve()
            and threading.current_thread().name == "confirm-thread"
            and not cleanup_done.is_set()
        ):
            if not cleanup_done.wait(timeout=2):
                raise AssertionError("cleanup thread tidak selesai tepat waktu")
        return original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(mod, "_processing_paths", ProcessingSet())
    monkeypatch.setattr(type(path), "unlink", coordinated_unlink)
    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: {
            "batch_id": 123456,
            "record_count": 1,
            "total_ton": "1.0000",
        },
    )
    with mod._lock:
        mod._pending[token] = {
            "path": path,
            "kind": "actual",
            "filename": "cleanup-thread-race.xlsx",
            "expires": time.monotonic() + 600,
        }

    cleanup_thread = threading.Thread(
        target=run_cleanup,
        name="cleanup-thread",
        daemon=True,
    )
    confirm_result = []
    confirm_errors = []

    def run_confirm():
        try:
            confirm_result.append(
                mod.import_confirm(mod.ConfirmRequest(token=token))
            )
        except BaseException as exc:  # propagate assertion from worker thread
            confirm_errors.append(exc)

    confirm_thread = threading.Thread(
        target=run_confirm,
        name="confirm-thread",
        daemon=True,
    )

    try:
        cleanup_thread.start()
        confirm_thread.start()
        confirm_thread.join(timeout=3)
        cleanup_thread.join(timeout=3)

        assert not confirm_thread.is_alive(), "confirm thread menggantung"
        assert not cleanup_thread.is_alive(), "cleanup thread menggantung"
        assert not confirm_errors, confirm_errors
        assert not cleanup_errors, cleanup_errors
        assert confirm_result[0]["status"] == "success"
        assert not path.exists(), "file staging belum dibersihkan"
        with mod._lock:
            assert token not in mod._pending
            assert path not in mod._processing_paths
    finally:
        with mod._lock:
            mod._pending.pop(token, None)
            mod._processing_paths.discard(path)
        mod._processing_paths = original_processing_paths
        path.unlink(missing_ok=True)
