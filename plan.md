# Rencana Pengembangan Dashboard PEMS

Status: audit awal selesai; belum ada perubahan kode produksi, SQL, atau database.

## 1. Baseline yang diaudit

Repository yang diaudit adalah checkout lokal PEMS pada branch `dashboard-period-filter`, berbasis `origin/main` commit `1271588`. Branch pengembangan ini belum digabung ke `main`; keputusan integrasi tetap menunggu review.

Komponen yang diperiksa:

- `README.md`: arsitektur FastAPI, PostgreSQL, dashboard browser lokal, workflow impor Excel, aturan keamanan, dan prosedur test.
- `app/main.py`: endpoint `/health`, `/api/summary`, `/api/estates`, `/api/divisions`, `/dashboard`, serta registrasi endpoint impor dengan `PEMS_IMPORT_API_KEY`.
- `app/import_routes.py`: preview/confirm, token single-use, `_pending`, `_uploading_paths`, `_processing_paths`, cleanup staging, audit failure, dan pengamanan race condition.
- `app/import_service.py`: validasi workbook, profil DB LHK REGION MTD, presisi `NUMERIC(14,4)`, hash file, dan transaksi impor.
- `sql/schema.sql`, `sql/002_production_actuals.sql`, `sql/003_reference_data.sql`, `sql/004_dashboard_views.sql`.
- `app/static/index.html`: KPI, filter estate, grafik per estate, tabel/kartu divisi, sorting, loading/error/empty state, responsive mobile layout, dan modal impor.
- `tests/` dan `.github/workflows/test.yml`.

## 2. Rumus bisnis yang terverifikasi

View `v_pems_comparison_division` mengambil batch budget terbaru dan batch actual terbaru secara terpisah berdasarkan `report_date DESC, id DESC`, kemudian:

- budget per divisi = `SUM(production_budgets.budget_ton)` pada batch budget terbaru;
- realisasi per divisi = `SUM(production_actuals.actual_ton)` pada batch actual terbaru;
- selisih = realisasi - budget;
- pencapaian = `100 * realisasi / budget`, dengan `NULLIF(budget, 0)` untuk mencegah pembagian nol.

View estate menjumlahkan nilai per divisi. Endpoint summary menjumlahkan view divisi dan menggunakan rumus pencapaian yang sama. Frontend menggunakan nilai tersebut untuk kondisi semua estate, dan menghitung ulang subtotal untuk filter estate.

## 3. Kapabilitas yang sudah tersedia

Dashboard saat ini sudah memiliki:

- empat KPI utama: budget, realisasi, selisih, pencapaian;
- grafik perbandingan budget vs realisasi per estate;
- filter estate;
- tabel desktop dan kartu divisi mobile;
- sorting divisi berdasarkan estate, pencapaian, atau selisih;
- format tonase tanpa desimal pada tampilan;
- loading, empty state, status koneksi, dan pesan error;
- import preview/confirm dengan API key, token sekali pakai, dan cleanup staging.

## 4. Temuan dan risiko

### Prioritas tinggi: periode budget dan aktual dapat tidak selaras

SQL memilih batch terbaru budget dan actual secara independen. Jika tanggal laporan berbeda, dashboard tetap membandingkannya. Ini berisiko terutama karena actual DB LHK REGION bersifat MTD, sedangkan periode budget perlu diverifikasi dari workbook budget. Tidak boleh mengubah rumus sebelum definisi periode bisnis disepakati.

Rencana: tambahkan indikator status periode (`selaras`, `berbeda`, atau `belum lengkap`) dan uji query dengan tanggal berbeda. Keputusan apakah dashboard harus menolak perbandingan lintas periode atau hanya memberi peringatan harus dikonfirmasi sebelum implementasi.

### Prioritas menengah: belum ada filter divisi

Filter estate sudah menyaring grafik, KPI, insight, dan daftar divisi secara konsisten di frontend. Belum ada filter divisi yang dapat dipakai untuk fokus ke satu divisi. Rencana: tambahkan filter divisi yang bergantung pada estate terpilih dan terapkan pada KPI, grafik, insight, serta tabel/kartu.

### Prioritas menengah: coverage rumus/dashboard belum cukup

Test yang tersedia kuat pada impor, staging, rollback, dan validasi workbook, tetapi belum memiliki test integrasi yang memverifikasi hasil view/API untuk kombinasi data budget, actual, null budget, data kosong, dan tanggal laporan berbeda.

Rencana: tambah fixture database test dan test kontrak SQL/API sebelum perubahan frontend besar.

### Prioritas rendah: format persentase

Frontend saat ini menampilkan persentase dengan dua angka desimal, sedangkan standar tampilan proyek meminta tidak menampilkan angka desimal pada tampilan website. Rencana: gunakan persentase bulat di UI, tetap mempertahankan presisi SQL untuk perhitungan dan audit.

### Prioritas rendah: rendering berbasis `innerHTML`

Nilai kode/nama dari database dimasukkan ke template HTML melalui `innerHTML`. Data saat ini berasal dari reference data terkontrol, tetapi penggunaan `textContent` atau escaping terpusat akan mengurangi risiko jika data reference berubah.

## 5. Rencana implementasi bertahap

### Fase A — Kontrak data dan periode

- Tambahkan test integrasi pada database `pems_test_import` untuk view divisi, view estate, dan summary.
- Uji budget/actual lengkap, salah satu batch kosong, budget nol, actual nol, dan tanggal laporan berbeda.
- Tambahkan metadata status periode tanpa mengubah tabel produksi.
- Pastikan tidak ada operasi tulis terhadap database produksi.

### Fase B — Filter dan API dashboard

- Pertahankan FastAPI dan view SQL yang ada.
- Tambahkan filter divisi secara konsisten, dengan estate sebagai filter induk.
- Hindari duplikasi rumus antara summary, estate, division, dan frontend jika endpoint gabungan atau parameter query dapat menjaga satu sumber kebenaran.
- Pertahankan endpoint impor dan seluruh kontrol keamanan yang sudah ada.

### Fase C — UI dashboard

- Pertahankan gaya visual profesional yang sudah ada; perbaiki hierarki informasi, bukan membangun ulang aplikasi.
- Tambahkan kontrol filter divisi, status periode, dan indikator data tidak lengkap.
- Pertahankan KPI utama sebagai empat kartu; detail tetap berada pada grafik/tabel.
- Gunakan tonase dan persentase tanpa desimal pada display website.
- Pertahankan grafik estate, sorting divisi, kartu mobile, loading, empty state, dan error state.
- Perbaiki rendering nilai dinamis agar tidak bergantung pada `innerHTML` untuk nilai data.

### Fase D — Validasi dan PR

- Jalankan seluruh test suite pada database uji terisolasi.
- Jalankan compile, lint, dan validasi sintaks JavaScript.
- Preview dashboard hanya terhadap database uji/read-only.
- Review diff, status Git, dan file sensitif.
- Buat branch pengembangan dashboard terpisah dari baseline yang disepakati.
- Push branch dan ajukan Pull Request; jangan merge otomatis ke `main`.

## 6. Keputusan yang diperlukan sebelum implementasi

1. Apakah budget dan actual harus dibandingkan hanya jika `budget_report_date == actual_report_date`, atau boleh berbeda dengan peringatan yang jelas?
2. Apakah filter divisi harus dihitung pada server melalui parameter API, atau cukup pada dataset yang sudah diambil frontend selama jumlah data tetap kecil dan hasil KPI konsisten?
3. Apakah tampilan persentase bulat tanpa desimal disetujui untuk semua KPI, tabel, grafik, dan insight?

## 7. Hasil baseline audit

- Test suite: `14 passed in 2.81s`.
- Compile Python: berhasil.
- Ruff `E9,F`: berhasil.
- `git diff --check`: berhasil.
- Sintaks JavaScript dashboard: berhasil.
- Database produksi: tidak digunakan.
- Kode aplikasi, SQL, dan konfigurasi produksi: tidak diubah selama audit.
