# PEMS Installer v1.0

Paket aplikasi PEMS untuk Termux Android.

## Instalasi
1. Ekstrak ZIP ke folder instalasi baru.
2. Jalankan `bash installer/install.sh`.
3. Tentukan `DATABASE_URL` secara eksplisit.
4. Terapkan `sql/schema.sql`, `sql/005_authentication.sql`, `sql/003_reference_data.sql`, lalu `sql/004_dashboard_views.sql`.
5. Tentukan `PEMS_IMPORT_API_KEY` secara lokal.
6. Jalankan `bash installer/start.sh`.
7. Buka `http://127.0.0.1:8000/dashboard`.

Installer tidak menjalankan SQL dan tidak membuat, menghapus, atau mengubah database secara otomatis.

Sebelum deployment HTTPS, jalankan readiness check tanpa menampilkan secret:

```bash
PEMS_ENV=production PEMS_COOKIE_SECURE=true \
  python scripts/predeploy_check.py
```

Readiness check hanya memeriksa konfigurasi dan keberadaan file migrasi. Script
tidak menguji koneksi atau menulis database.

## Catatan
- Pastikan PostgreSQL sudah berjalan.
- Untuk pengujian gunakan database terpisah, misalnya `postgresql:///pems_test_import`.
- Jangan memilih database utama sebelum backup dan pemeriksaan konfigurasi.
- Backup database perlu dilakukan secara terpisah menggunakan `pg_dump`.
- Endpoint impor memerlukan header `X-PEMS-Import-Key` yang nilainya sama dengan `PEMS_IMPORT_API_KEY`.

## Clipboard output Termux

Pasang dukungan clipboard dan jalankan helper:

```bash
pkg install termux-api
bash installer/copy-output.sh python -m pytest -q
```

Output tetap tampil di terminal dan otomatis disalin ke clipboard Android.
Helper juga mendukung pipe, file, dan teks langsung:

```bash
git diff | bash installer/copy-output.sh
bash installer/copy-output.sh --file hasil-test.txt
bash installer/copy-output.sh --text 'teks yang ingin disalin'
```

Aplikasi Termux:API juga harus terpasang dari sumber yang sama dengan Termux.
