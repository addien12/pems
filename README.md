# PEMS — Palm Estate Monitoring System

Aplikasi monitoring produksi perkebunan kelapa sawit berbasis Python, FastAPI, dan PostgreSQL untuk Termux Android.

## Cakupan

- 6 estate aktif: MAGE, BMKE, BKCE, BBGE, BHPE, SPGE.
- 24 divisi aktif.
- Perbandingan anggaran dan realisasi produksi.
- Dashboard melalui browser lokal.
- Impor Excel dengan preview dan konfirmasi.
- Riwayat impor dan audit.
- Pengujian integritas data dan transaksi impor.

## Persyaratan

- Termux Android.
- Python dan virtual environment.
- PostgreSQL dan libpq.

## Instalasi

Perbarui paket Termux:

```bash
pkg update
pkg install python postgresql libpq -y
```

Aktifkan virtual environment proyek:

```bash
cd ~/pems
python -m venv .venv
source .venv/bin/activate
```

Instalasi dependensi:

```bash
python -m pip install -r installer/requirements.txt
```

Untuk pengembangan dan pengujian, gunakan dependensi tambahan:

```bash
python -m pip install -r requirements-dev.txt
```

## Konfigurasi database

Pastikan PostgreSQL berjalan dan database tujuan sudah dibuat.

Atur DATABASE_URL sesuai konfigurasi lokal. Contoh format:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@127.0.0.1:5432/NAMA_DATABASE'
```

Ganti USER, PASSWORD, dan NAMA_DATABASE dengan konfigurasi lokal yang benar.
Jangan menaruh kata sandi asli dalam README atau repositori Git.

PEMS tidak menjalankan migrasi skema database secara otomatis ketika server dimulai. Pastikan skema yang diperlukan sudah diterapkan secara terencana.

Urutan penerapan database untuk instalasi baru:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
psql "$DATABASE_URL" -f sql/003_reference_data.sql
psql "$DATABASE_URL" -f sql/004_dashboard_views.sql
```

File `sql/002_production_actuals.sql` disediakan untuk database lama yang sudah
memakai `schema.sql` versi sebelumnya. Untuk instalasi baru, tabel actual sudah
tercakup dalam `schema.sql`; menjalankan file tersebut juga aman karena bersifat
idempoten.

## Menjalankan aplikasi

Setelah virtual environment aktif dan DATABASE_URL dikonfigurasi:

```bash
bash installer/start.sh
```

Dashboard: http://127.0.0.1:8000/dashboard
Pemeriksaan kesehatan: http://127.0.0.1:8000/health
```

Endpoint impor dilindungi API key. Sebelum menjalankan server, tentukan key
secara lokal dan jangan commit nilainya ke Git:

```bash
export PEMS_IMPORT_API_KEY='ganti-dengan-random-string-panjang'
```

Kirim key tersebut melalui header `X-PEMS-Import-Key` pada request preview dan
confirm. Jika key belum dikonfigurasi, endpoint impor akan menolak request.

## Workflow impor harian DB LHK REGION

Workbook `DB_LHK_PANEN_REGION_YYYY-MM-DD.xlsx` dapat diunggah melalui menu
**Impor Data Excel** dengan jenis **Produksi Aktual**. PEMS membaca sheet
`Produksi Tahun Ini` sebagai data month-to-date (MTD), mulai tanggal 1 sampai
tanggal laporan di sel `B3`, memetakan 24 divisi aktif, dan menyimpan setiap
tanggal harian sebagai record realisasi produksi.

Untuk operasi Termux, validasi file terlebih dahulu tanpa mengubah database:

```bash
DATABASE_URL='postgresql://127.0.0.1:5432/NAMA_DATABASE' \
  python scripts/import_actual.py \
  /path/DB_LHK_PANEN_REGION_2026-10-20.xlsx
```

Jika ringkasan tanggal, jumlah record, dan total ton sudah benar, jalankan
`--commit` pada database yang memang ditujukan untuk operasional:

```bash
DATABASE_URL='postgresql://127.0.0.1:5432/NAMA_DATABASE' \
  PEMS_IMPORT_USER='operator' \
  python scripts/import_actual.py \
  /path/DB_LHK_PANEN_REGION_2026-10-20.xlsx --commit
```

PEMS menolak file identik berdasarkan SHA-256, menyimpan histori batch dan audit,
serta memilih batch actual dengan tanggal laporan terbaru untuk dashboard. File
yang sama atau file produksi tidak boleh dimasukkan ke repository Git.

## Pengujian

Jalankan pengujian hanya setelah database pengujian terpisah disiapkan:

```bash
python -m pytest -q
```

Test integrasi rollback hanya berjalan jika `DATABASE_URL` menunjuk tepat ke
database bernama `pems_test_import`.

Jangan menjalankan pengujian yang dapat mengubah database produksi.

## Struktur proyek

- app/: aplikasi dan endpoint API.
- installer/: skrip instalasi dan pengelolaan server.
- scripts/: skrip inspeksi dan impor data.
- sql/: skema dan definisi SQL.
- tests/: pengujian.
- imports/: data impor lokal, tidak untuk repositori.
- logs/ dan backups/: data operasional lokal.

## Keamanan dan integritas data

- Jangan memasukkan kata sandi, token, atau kredensial ke Git.
- Jangan mengunggah workbook produksi, log, atau cadangan ke repositori.
- Pertahankan riwayat impor dan audit.
- Cadangkan database sebelum perubahan skema atau pemeliharaan.
- Validasi data sebelum mengubah database produksi.

## Status proyek

Dokumentasi ini menjelaskan struktur dan penggunaan dasar PEMS. Validasi lebih lanjut tetap diperlukan sebelum penggunaan operasional produksi.
