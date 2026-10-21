# PEMS Installer v1.0

Paket aplikasi PEMS untuk Termux Android.

## Instalasi
1. Ekstrak ZIP ke folder instalasi baru.
2. Jalankan `bash installer/install.sh`.
3. Tentukan `DATABASE_URL` secara eksplisit.
4. Terapkan `sql/schema.sql`, `sql/003_reference_data.sql`, lalu `sql/004_dashboard_views.sql`.
5. Tentukan `PEMS_IMPORT_API_KEY` secara lokal.
6. Jalankan `bash installer/start.sh`.
7. Buka `http://127.0.0.1:8000/dashboard`.

Installer tidak menjalankan SQL dan tidak membuat, menghapus, atau mengubah database secara otomatis.

## Catatan
- Pastikan PostgreSQL sudah berjalan.
- Untuk pengujian gunakan database terpisah, misalnya `postgresql:///pems_test_import`.
- Jangan memilih database utama sebelum backup dan pemeriksaan konfigurasi.
- Backup database perlu dilakukan secara terpisah menggunakan `pg_dump`.
- Endpoint impor memerlukan header `X-PEMS-Import-Key` yang nilainya sama dengan `PEMS_IMPORT_API_KEY`.
