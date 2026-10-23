import time

import app.import_routes as mod


def test_successful_import_is_not_reported_as_failed_when_cleanup_fails(
    monkeypatch, tmp_path
):
    path = tmp_path / "cleanup_error_probe.xlsx"
    path.write_bytes(b"isolated test data")
    token = "cleanup-error-isolated-token"
    item = {
        "path": path,
        "kind": "budget",
        "filename": "cleanup_error_probe.xlsx",
        "expires": time.monotonic() + 600,
    }

    with mod._lock:
        mod._pending[token] = item

    monkeypatch.setattr(
        mod,
        "cleanup_expired",
        lambda: None,
    )
    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: {"import_batch_id": 999999},
    )

    original_unlink = type(path).unlink

    def fail_target_unlink(self, *args, **kwargs):
        if self == path:
            raise OSError("simulated staging cleanup failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "unlink", fail_target_unlink)

    try:
        result = mod.import_confirm(mod.ConfirmRequest(token=token))

        assert result["status"] == "success"
        assert result["import_batch_id"] == 999999
        assert token not in mod._pending
        assert path not in mod._processing_paths
        assert path.exists()
    finally:
        monkeypatch.setattr(type(path), "unlink", original_unlink)
        with mod._lock:
            mod._pending.pop(token, None)
            mod._processing_paths.discard(path)
            mod._uploading_paths.discard(path)
        path.unlink(missing_ok=True)
