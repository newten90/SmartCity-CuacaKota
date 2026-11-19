Model yang disarankan: **Opus**, effort **high**. Pekerjaannya menyentuh banyak berkas, harus menjaga angka tetap sama dengan versi Streamlit, dan menulis ulang pengujian.

---

Kamu bekerja di repo **SmartCity-CuacaKota** (dashboard cuaca Bandung, Jakarta, Surabaya untuk tugas Telematika). Tugasmu: **migrasikan tampilan dari Streamlit ke aplikasi web biasa** sesuai desain di folder `desain/`, tanpa mengubah perilaku data.

## Aturan keras
- **Jangan pernah `git commit`, `git push`, membuat branch, atau membuka PR.** Saya yang commit dan push sendiri. Boleh `git status` / `git diff`.
- Jangan ubah isi `laporan/`, `bukti/`, `data/*.json`, `data/cuaca_udara.csv`, `supabase.sql`, dan `.streamlit/secrets.toml`.
- Jangan tampilkan atau mencetak isi `SUPABASE_DB_URL` atau token di log/output.
- `sensor.py`, `ambil_data.py`, `analisis.py`, `cuaca_online.py`, dan `penyimpanan.py` dipakai apa adanya. Kalau perlu memindahkan fungsi dari `app.py` (mis. `online_history()`, `correlation()`), pindahkan ke modul Python tanpa mengubah logikanya.
- Bahasa UI dan pesan: Indonesia. Semua waktu WIB.
- Hanya alat gratis/open source.

## Baca dulu
1. `desain/README.md`: spesifikasi tiap halaman, komponen, sumber data, dan teks pesan state.
2. `desain/tokens.css`: warna, huruf (Manrope), radius, jarak.
3. `desain/referensi/*.html`: buka/baca sebagai acuan visual. Angka di dalamnya contoh; **jangan disalin sebagai data**.
4. Seluruh kode Python di root, `README.md`, `requirements.txt`, `uji.py`, `uji_sensor.py`.

## Stack target
- **Backend:** FastAPI + uvicorn (`main.py`). Menyajikan JSON API dan berkas statis.
- **Frontend:** HTML + CSS + JavaScript biasa di `static/` (tanpa build step, tanpa framework). Grafik pakai **Plotly.js** (repo sudah memakai Plotly), dimuat dari CDN resmi atau berkas lokal.
- Tetap jalan di Windows PowerShell dengan Python 3.12/3.13 dan `.venv`, seperti README sekarang.
- Koneksi Supabase tetap lewat `penyimpanan.session()`. Jika URI kosong atau gagal, pakai fallback yang sama seperti sekarang (SQLite untuk sensor, `data/riwayat_online.csv` untuk riwayat).

## Endpoint minimal
| Endpoint | Isi | Dari |
|---|---|---|
| `GET /api/kota` | daftar kota + koordinat | `ambil_data.CITIES` |
| `GET /api/cuaca?kota=` | current, 24 jam, 7 hari; cache 15 menit; 503 + pesan bila Open-Meteo gagal | `cuaca_online.outlook()` |
| `GET /api/riwayat?kota=` | baris per jam + label sumber ("Supabase" / "salinan impor di repositori") | logika `online_history()` |
| `GET /api/riwayat.csv?kota=` | unduhan CSV | sama |
| `GET /api/analisis?kota=&dari=&sampai=` | 4 indikator, harian, bulanan (+`bulan_utuh`), tabel 3 kota, jumlah nilai valid, korelasi | `analisis.aggregate()`, `monthly()`, `correlation()` |
| `GET /api/analisis.csv?kota=&dari=&sampai=` | unduhan CSV kota & periode | sama dengan tombol unduh sekarang |
| `GET /api/sensor?kota=` | perangkat, 60 baris terakhir per sensor, suhu model di jam yang sama | `Store.devices()`, `Store.history()`, riwayat |

Validasi parameter (kota harus salah satu dari tiga, tanggal di 2025, `dari ≤ sampai`) dengan pesan 400 yang jelas. Nilai NaN dikirim sebagai `null`.

## Halaman (lihat `desain/README.md` untuk detail)
`/` Cuaca · `/analisis` · `/riwayat` · `/sensor` · `/kota`, dengan rail navigasi kiri di desktop dan tab bar bawah di layar < ±900 px. Kota terpilih disimpan di `?kota=` + localStorage dan dipakai di semua halaman. Terapkan semua state gagal/kosong/memuat beserta teks pesannya.

## Pengujian
- Tulis ulang `uji.py` tanpa `streamlit.testing`: pakai `fastapi.testclient.TestClient`. Pertahankan cek yang sama: 26.280 baris tanpa duplikat & tanpa NaN, **48 nilai indikator** (3 kota × 4 periode × 4 variabel) dari `/api/analisis` cocok dengan hitungan Pandas sampai 2 desimal, tulis hasil ke `bukti/uji_indikator.csv` dengan kolom yang sama, cek hujan kosong → total `null` dan `bulan_utuh` false.
- Tambah uji endpoint: kota tidak valid → 400, fallback riwayat ke CSV saat database tidak tersedia, `/api/cuaca` mengembalikan 503 saat `outlook()` dibuat gagal (mock, tanpa internet).
- `python -m unittest uji_sensor` harus tetap lulus tanpa perubahan.
- Jalankan semua tes dan laporkan hasilnya.

## Pembersihan & dokumentasi
- Setelah versi baru lulus uji: hapus `app.py` dan `tampilan_cuaca.py` (pindahkan dulu tabel `CONDITIONS` ke modul lain). Keluarkan `streamlit` dari `requirements.txt`, lalu tambahkan `fastapi`, `uvicorn` (dan `httpx` untuk TestClient) dengan versi dikunci seperti gaya file sekarang.
- `penyimpanan.cloud_url()` boleh tetap membaca `.streamlit/secrets.toml` agar setup tim tidak rusak. Tambahkan juga dukungan `.env` hanya jika sederhana, dan dokumentasikan.
- Perbarui `README.md`: cara menjalankan (`.\.venv\Scripts\python -m uvicorn main:app --reload`), daftar halaman dan endpoint, bagian Supabase/sensor yang tetap berlaku, cara uji. Ganti bagian Streamlit Community Cloud dengan panduan deploy ke Vercel (lihat bagian Vercel di bawah). **Jangan deploy sendiri**; saya yang menghubungkan repo ke Vercel.

## Siapkan untuk Vercel
Hosting memakai **Vercel** (Python runtime, FastAPI dideteksi otomatis). Cek dokumentasi resmi Vercel untuk FastAPI sebelum menentukan nama berkas entrypoint dan letak berkas statis; jangan menebak.
- Instance FastAPI bernama `app` di entrypoint yang didukung Vercel. Tambahkan `.python-version` (3.12 atau 3.13).
- Aplikasi di Vercel jalan sebagai fungsi serverless, jadi:
  - **Penerima sensor**: tambahkan `POST /pengukuran` di FastAPI yang memakai ulang `sensor.measurement()` dan `Store.save()` dengan aturan token Bearer (`SENSOR_TOKEN` dari environment) dan kode balasan yang sama (201/200/400/401/409/503, batas 4096 byte). Dengan begitu ESP32 bisa mengirim ke URL HTTPS publik. `sensor.py` tetap ada untuk mode lokal. Tambahkan uji untuk endpoint ini yang meniru `uji_sensor.py`.
  - **Tanpa Supabase tidak ada penyimpanan permanen** di Vercel. Di produksi, `SUPABASE_DB_URL` wajib diisi lewat Environment Variables Vercel (`penyimpanan.cloud_url()` sudah membaca env lebih dulu). Fallback SQLite cukup untuk lokal; kalau env kosong di Vercel, tampilkan pesan yang jelas, bukan error 500.
  - **Cache prakiraan** jangan hanya mengandalkan memori proses. Pakai header `Cache-Control` (mis. `s-maxage=900, stale-while-revalidate`) di `/api/cuaca`, tetap dengan batas 15 menit.
  - Koneksi Postgres dibuka per permintaan dengan timeout pendek, seperti sekarang. Gunakan URI pooler Supabase.
- Pastikan ukuran bundel fungsi kecil: kecualikan `laporan/`, `bukti/`, `desain/`, `data/*.json`, dan `.venv` dari fungsi (lewat `vercel.json` / `.vercelignore` sesuai dokumentasi), tapi **sertakan** `data/cuaca_udara.csv`, `data/riwayat_online.csv`, dan berkas yang dibaca analisis. Laporkan perkiraan ukuran dependensi.
- Jangan simpan rahasia di repo. Tulis daftar Environment Variables yang harus saya isi di Vercel (`SUPABASE_DB_URL`, `SENSOR_TOKEN`).
- Uji dengan `vercel dev` bila Vercel CLI tersedia; kalau tidak ada, cukup uvicorn lokal dan sebutkan di ringkasan.

## Rapikan sinkronisasi riwayat (`cuaca_online.py`)
Sekarang satu berkas memegang dua tugas berbeda dan sinkronnya hanya jalan kalau dijalankan manual. Perbaiki tanpa mengubah isi data:
- Pisahkan: `prakiraan.py` berisi `fetch()` dan `outlook()` untuk dashboard; `sinkron_riwayat.py` berisi `city_history()` dan `sync()`. Perbarui semua import.
- Sinkron **inkremental**: hanya ambil ulang ~10 hari terakhir (cukup untuk mengganti baris "Best Match" dengan ERA5 setelah ERA5 tersedia), bukan seluruh data sejak 1 Oktober setiap kali. Tetap sediakan opsi `--penuh` untuk impor ulang dari 1 Oktober 2026.
- Jangan gagal total hanya karena satu jam kosong: catat jam yang kosong, simpan yang lengkap, dan keluarkan ringkasan.
- Penulisan `data/riwayat_online.csv` hanya terjadi saat dijalankan dari laptop (opsi `--csv`), karena di Vercel berkas proyek tidak bisa ditulis.
- Jadwal otomatis: buat workflow **GitHub Actions** terjadwal (mis. tiap 3 jam) yang menjalankan `python sinkron_riwayat.py` dengan secret `SUPABASE_DB_URL`. Jangan pakai Vercel Cron, karena paket Hobby hanya mengizinkan sekali sehari. Tulis cara mengisi secret di README. Workflow tidak boleh commit atau push apa pun.
- Di halaman Riwayat, tampilkan waktu sinkron terakhir dan beri tanda bila datanya lebih tua dari 6 jam.
- Tambahkan uji untuk logika potong rentang tanggal (ERA5 vs model operasional) memakai data tiruan, tanpa internet.

## Cara kerja
1. Baca semua bahan, lalu tulis rencana singkat (berkas baru/diubah/dihapus) sebelum mulai.
2. Bangun backend + tes API dulu, pastikan 48 nilai cocok, baru kerjakan frontend.
3. Jalankan server lokal dan buka tiap halaman di desktop dan lebar HP untuk mengecek tampilannya terhadap `desain/referensi/`.
4. Akhiri dengan ringkasan: berkas yang berubah, hasil tes, hal yang belum selesai atau perlu keputusan saya, dan langkah deploy ke Vercel yang harus saya lakukan sendiri. Ingat: **tanpa commit dan push.**
