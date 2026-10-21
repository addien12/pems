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

Instal dependensi:

```bash
python -m pip install -r installer/requirements.txt
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

## Menjalankan aplikasi

Setelah virtual environment aktif dan DATABASE_URL dikonfigurasi:

```bash
bash installer/start.sh
```

Dashboard: http://127.0.0.1:8000/dashboard
Pemeriksaan kesehatan: http://127.0.0.1:8000/health

## Pengujian

Jalankan pengujian hanya setelah database pengujian terpisah disiapkan:

```bash
python -m pytest -q
```

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
