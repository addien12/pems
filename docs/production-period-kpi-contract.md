# Kontrak Periode dan KPI Produksi PEMS

Dokumen ini menjadi fondasi untuk dashboard produksi harian, bulanan, ranking Estate, dan ranking Divisi. PR ini hanya menetapkan jendela tanggal dan kontrak API; belum menghitung atau mengubah nilai produksi di database.

## Prinsip sumber tanggal

`as_of_date` harus berasal dari tanggal laporan terakhir pada workbook DB LHK REGION yang sudah lolos validasi. Tanggal perangkat atau tanggal server hanya boleh dipakai sebagai fallback teknis dan harus ditampilkan sebagai `server_date`, bukan dianggap sebagai bukti data produksi terbaru.

## Jendela periode

Semua rentang bersifat inklusif pada `start_date` dan `end_date`.

| Key | Definisi |
|---|---|
| `today` | Tanggal laporan `as_of_date` saja. |
| `previous_day` | Satu hari kalender sebelum `as_of_date`. |
| `month_to_date` | Hari pertama bulan `as_of_date` sampai `as_of_date`. |
| `previous_month_to_date` | Hari pertama bulan sebelumnya sampai tanggal kalender yang ekuivalen; akhir bulan disesuaikan untuk Februari atau bulan yang lebih pendek. |
| `year_to_date` | 1 Januari tahun `as_of_date` sampai `as_of_date`. |
| `previous_year_to_date` | 1 Januari tahun sebelumnya sampai tanggal kalender yang ekuivalen. |

Contoh untuk `as_of_date=2026-10-16`:

- `today`: 2026-10-16 sampai 2026-10-16.
- `previous_day`: 2026-10-15 sampai 2026-10-15.
- `month_to_date`: 2026-10-01 sampai 2026-10-16.
- `previous_month_to_date`: 2026-09-01 sampai 2026-09-16.
- `year_to_date`: 2026-01-01 sampai 2026-10-16.
- `previous_year_to_date`: 2025-01-01 sampai 2025-10-16.

## Istilah SD HI dan SD BI

Arti resmi SD HI dan SD BI belum dipaksakan oleh kode karena perlu konfirmasi dari pemilik proses bisnis. API mengembalikan status `pending_business_confirmation` agar UI tidak menampilkan label yang berpotensi salah.

Kandidat teknis yang saat ini dicatat untuk review:

- SD HI kandidat: `month_to_date`.
- SD BI kandidat: `year_to_date`.

Kandidat tersebut bukan keputusan final dan tidak boleh digunakan sebagai angka resmi sebelum dikonfirmasi.

## Endpoint kontrak

```http
GET /api/production/periods?as_of=2026-10-16
```

Endpoint bersifat read-only dan tidak membuka koneksi database. Respons minimal:

```json
{
  "as_of_date": "2026-10-16",
  "as_of_source": "query",
  "periods": {
    "today": {
      "key": "today",
      "start_date": "2026-10-16",
      "end_date": "2026-10-16"
    }
  },
  "business_labels": {
    "sd_hi": {
      "status": "pending_business_confirmation",
      "candidate_period": "month_to_date"
    },
    "sd_bi": {
      "status": "pending_business_confirmation",
      "candidate_period": "year_to_date"
    }
  }
}
```

Endpoint agregasi produksi berikutnya harus memakai key periode ini, filter Estate/Divisi yang sama, dan sumber tanggal laporan yang sama. Nilai `0` tidak boleh digunakan untuk menggantikan data yang belum tersedia; kondisi kosong harus dikembalikan sebagai status data kosong.

## Kontrak KPI lanjutan

Setelah definisi bisnis disetujui, endpoint agregasi akan menyediakan minimal:

- `actual_ton` untuk realisasi produksi.
- `budget_ton` untuk target yang memang tersedia pada periode yang sama.
- `variance_ton = actual_ton - budget_ton`.
- `achievement_pct = actual_ton / budget_ton * 100` jika budget bukan nol.
- Metadata `as_of_date`, `period_key`, `period_status`, dan `period_warning`.

Perhitungan tidak boleh mencampur periode budget dan aktual yang tanggal laporannya berbeda tanpa peringatan.
