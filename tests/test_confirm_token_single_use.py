import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.import_routes as mod
from fastapi import HTTPException

mod.STAGING.mkdir(parents=True, exist_ok=True)

fd, filename = tempfile.mkstemp(
    prefix="token_probe_",
    suffix=".xlsx",
    dir=mod.STAGING,
)
import os
os.close(fd)

path = Path(filename)
token = "isolated-single-use-token"

original_save_import = mod.save_import

try:
    path.write_bytes(b"dummy isolated token test")

    with mod._lock:
        mod._pending[token] = {
            "path": path,
            "kind": "budget",
            "filename": "token_probe.xlsx",
            "expires": time.monotonic() + 600,
        }

    # Stub: memastikan tes tidak menyimpan apa pun ke database.
    mod.save_import = lambda *args, **kwargs: {
        "batch_id": 999999,
        "record_count": 0,
        "total_ton": "0",
    }

    first = mod.import_confirm(mod.ConfirmRequest(token=token))
    assert first["status"] == "success"
    assert not path.exists(), "File sementara tidak dibersihkan."
    print("LULUS: konfirmasi pertama menghabiskan token.")
    print("LULUS: file sementara dibersihkan.")

    try:
        mod.import_confirm(mod.ConfirmRequest(token=token))
    except HTTPException as exc:
        assert exc.status_code == 410, f"Status tidak sesuai: {exc.status_code}"
        print("LULUS: penggunaan token kedua ditolak dengan HTTP 410.")
    else:
        raise AssertionError("Token dapat digunakan lebih dari sekali.")

finally:
    mod.save_import = original_save_import
    with mod._lock:
        mod._pending.pop(token, None)
        mod._processing_paths.discard(path)
    path.unlink(missing_ok=True)
