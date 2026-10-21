#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "PEMS Installer v1.0"
echo "Folder aplikasi: $ROOT"
echo "Database tidak akan dibuat atau dimigrasikan oleh skrip ini."

if ! command -v python >/dev/null 2>&1; then
    echo "ERROR: Python tidak ditemukan. Pasang Python di Termux terlebih dahulu."
    exit 1
fi

if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

.venv/bin/python -m pip install -r installer/requirements.txt
.venv/bin/python -m py_compile \
    app/main.py \
    app/import_routes.py \
    app/import_service.py

echo
echo "Instalasi dependensi selesai."
echo "Tentukan DATABASE_URL secara eksplisit sebelum menjalankan server."
echo "Contoh pengujian: export DATABASE_URL='postgresql:///pems_test_import'"
echo "Jalankan: bash installer/start.sh"
