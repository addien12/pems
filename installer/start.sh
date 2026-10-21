#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
    echo "ERROR: Virtual environment belum tersedia."
    echo "Jalankan bash installer/install.sh terlebih dahulu."
    exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL belum ditentukan."
    echo "Contoh pengujian:"
    echo "export DATABASE_URL='postgresql:///pems_test_import'"
    exit 1
fi

exec .venv/bin/python -m uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port 8000
