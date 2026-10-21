import os
import sys
import time
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.import_routes as mod


@pytest.fixture
def isolated_token_test(monkeypatch):
    mod.STAGING.mkdir(parents=True, exist_ok=True)

    fd, filename = tempfile.mkstemp(
        prefix="token_probe_",
        suffix=".xlsx",
        dir=mod.STAGING,
    )
    os.close(fd)

    path = Path(filename)
    token = "isolated-single-use-token"

    path.write_bytes(b"dummy isolated token test")

    with mod._lock:
        mod._pending[token] = {
            "path": path,
            "kind": "budget",
            "filename": "token_probe.xlsx",
            "expires": time.monotonic() + 600,
        }

    monkeypatch.setattr(
        mod,
        "save_import",
        lambda *args, **kwargs: {
            "batch_id": 999999,
            "record_count": 0,
            "total_ton": "0",
        },
    )

    try:
        yield token, path
    finally:
        with mod._lock:
            mod._pending.pop(token, None)
            mod._processing_paths.discard(path)

        path.unlink(missing_ok=True)


def test_confirmation_token_can_only_be_used_once(isolated_token_test):
    token, path = isolated_token_test

    first = mod.import_confirm(mod.ConfirmRequest(token=token))

    assert first["status"] == "success"
    assert not path.exists(), "File sementara tidak dibersihkan."

    with pytest.raises(HTTPException) as exc_info:
        mod.import_confirm(mod.ConfirmRequest(token=token))

    assert exc_info.value.status_code == 410
