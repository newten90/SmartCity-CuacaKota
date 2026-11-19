# Cuaca Kota

Dashboard cuaca Bandung, Jakarta, dan Surabaya. Semua jam memakai WIB. Aplikasinya web biasa: backend FastAPI (`main.py`) dengan halaman HTML, CSS, dan JavaScript biasa di `static/` (tanpa build step), grafik Plotly.js. Siap di-host di Vercel dengan data di Supabase.

Laporan minggu 2 memuat perkembangan proyek, data tiga kota, hasil pengujian, dan daftar pustaka. [Unduh laporan Word](https://github.com/newten90/SmartCity-CuacaKota/raw/refs/heads/main/laporan/Laporan-Akhir-Telematika.docx) · [Baca laporan](laporan/Laporan-Akhir-Telematika.md) · [Unduh PDF](laporan/Laporan-Akhir-Telematika.pdf). Tangkapan layar di laporan masih memperlihatkan tampilan Streamlit sebelum migrasi.

## Halaman

| Alamat | Isi |
|---|---|
| `/` | Cuaca: kondisi saat ini, suhu terasa, kelembapan, angin, PM2.5 terakhir, terbit/terbenam, tips hujan, per jam 24 jam, tujuh hari, ringkasan sensor. Prakiraan dari Open-Meteo, diperbarui paling sering tiap 15 menit. |
| `/analisis` | Analisis 2025: rentang tanggal, empat kartu, temuan, grafik suhu/hujan/PM2.5, tabel tiga kota, korelasi, unduh CSV. |
| `/riwayat` | Riwayat per jam sejak 1 Oktober 2026, sumber data, waktu sinkron terakhir (ditandai bila lebih dari 6 jam), grafik, tabel, unduh CSV. |
| `/sensor` | Pembacaan sensor IoT terakhir, perbandingan dengan model jam yang sama, tren, perangkat, tabel kiriman. |
| `/kota` | Pilih kota. Kota terpilih disimpan di `?kota=` dan `localStorage`, sama di semua halaman. |

Rail navigasi di kiri untuk desktop, tab bar di bawah untuk layar lebih sempit dari 900 px. Desain acuan ada di `desain/`.

## Menjalankan di komputer sendiri

Dari folder proyek, di PowerShell dengan Python 3.12 atau 3.13:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn main:app --reload
```

Buka `http://127.0.0.1:8000`. Arsip analisis dan salinan riwayat per jam sudah ada di folder `data`. Prakiraan membutuhkan internet.

Variabel lingkungan bisa ditaruh di berkas `.env` (baris `KUNCI=nilai`, tidak ikut git). Nilai yang sudah ada di lingkungan tidak ditimpa.

## Endpoint

| Endpoint | Isi |
|---|---|
| `GET /api/kota` | Daftar kota dan koordinat. |
| `GET /api/cuaca?kota=` | Saat ini, 24 jam, 7 hari. `503` dengan pesan bila Open-Meteo gagal. `Cache-Control: s-maxage=900`. |
| `GET /api/riwayat?kota=` (`&terbaru=N`) | Baris per jam, label sumber (`Supabase` atau `salinan impor di repositori`), jumlah, rentang, penanda data usang. |
| `GET /api/riwayat.csv?kota=` | Unduhan CSV riwayat. |
| `GET /api/analisis?kota=&dari=&sampai=` | Empat indikator, nilai valid, harian, bulanan (`bulan_utuh`), tabel tiga kota, korelasi, temuan. Tanggal `YYYY-MM-DD` di 2025, `dari` ≤ `sampai`. |
| `GET /api/analisis.csv?kota=&dari=&sampai=` | Unduhan CSV kota dan periode. |
| `GET /api/sensor?kota=` | Perangkat, 60 pengukuran terakhir per sensor, suhu model di jam yang sama. |
| `POST /pengukuran` | Penerima sensor (lihat bawah). |

Kota yang tidak dikenal atau tanggal yang salah mengembalikan `400` dengan pesan `{"pesan": "..."}`. Nilai kosong (NaN) dikirim sebagai `null`.

## Hubungkan ke Supabase

1. Buka proyek yang sudah ada di [Supabase Dashboard](https://supabase.com/dashboard). Buka **Connect**, pilih **Session pooler**, dan salin URI PostgreSQL-nya. [Panduan koneksi Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)
2. Isi `SUPABASE_DB_URL` di `.env`. Karakter khusus pada password ditulis dalam format URL, misalnya `@` menjadi `%40`.

   ```
   SUPABASE_DB_URL=postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres
   ```

3. Buat tabel `public.cuaca_sensor` dan `public.cuaca_online` serta cek koneksinya. Setup bisa diulang.

   ```powershell
   .\.venv\Scripts\python penyimpanan.py
   ```

Dengan URI kosong, penerima sensor lokal memakai SQLite di `data/sensor.sqlite3` dan riwayat memakai `data/riwayat_online.csv`. Jika Supabase tidak terjangkau, `/api/riwayat` otomatis memakai salinan CSV dan halaman Riwayat menampilkan labelnya. Koneksi Postgres dibuka per permintaan dengan batas waktu 5 detik.

## Kirim data sensor

Sensor mengirim `POST /pengukuran` dengan header `Authorization: Bearer <SENSOR_TOKEN>` dan JSON `{"sensor","kota","waktu","suhu","kelembapan"}`. `waktu` memakai ISO 8601 beserta zona, misalnya `2026-11-18T08:30:00+07:00`. Batas badan 4096 byte.

| Kode | Arti |
|---|---|
| 201 | pengukuran baru tersimpan |
| 200 | kiriman ulang yang sama |
| 400 | data di luar rentang atau bukan JSON yang benar |
| 401 | token salah |
| 409 | nilai berbeda untuk kota, sensor, dan waktu yang sama |
| 503 | database tidak terjangkau (kirim ulang dengan waktu pengukuran yang sama), atau `SENSOR_TOKEN`/`SUPABASE_DB_URL` belum diisi di server |

**Lewat aplikasi ini (dan di Vercel).** Setelah `uvicorn` berjalan atau setelah deploy, kirim ke `/pengukuran` pada alamatnya. Contoh dari PowerShell (ganti alamat dengan `https://NAMA-PROYEK.vercel.app` setelah deploy):

```powershell
$env:SENSOR_TOKEN = .\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:SENSOR_TOKEN   # salin nilainya, lalu jalankan uvicorn di terminal ini
.\.venv\Scripts\python -m uvicorn main:app
```

```powershell
$token = Read-Host 'Token penerima'
$body = @{
    sensor = 'demo-laptop'
    kota = 'Bandung'
    waktu = [DateTimeOffset]::Now.ToString('o')
    suhu = 26.4
    kelembapan = 78
} | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://127.0.0.1:8000/pengukuran' `
    -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json' -Body $body
```

**Penerima mandiri `sensor.py`** tetap tersedia untuk jaringan lokal: `SENSOR_TOKEN` diisi lalu `.\.venv\Scripts\python sensor.py` (port 8765, `--host 0.0.0.0` agar terjangkau ESP32 di Wi-Fi yang sama). Aturan token dan kode balasannya sama. Gunakan jaringan lokal tepercaya untuk HTTP ini. Di URL publik HTTPS (Vercel) ESP32 cukup memakai token penerima, tanpa URI database.

## Sinkron riwayat per jam

`sinkron_riwayat.py` mengambil riwayat per jam Open-Meteo dan memperbarui tabel `public.cuaca_online`. Pasangan kota dan waktu hanya mendapat satu baris meski diulang. Arsip memakai ERA5; enam hari terakhir memakai model operasional ("Best Match") karena ERA5 baru tersedia beberapa hari kemudian. PM2.5 dari CAMS via Open-Meteo.

```powershell
.\.venv\Scripts\python sinkron_riwayat.py           # inkremental: ambil ulang ~10 hari terakhir
.\.venv\Scripts\python sinkron_riwayat.py --penuh   # impor ulang sejak 1 Oktober 2026
.\.venv\Scripts\python sinkron_riwayat.py --csv     # dari laptop: perbarui juga data/riwayat_online.csv
```

Sinkron inkremental mengganti baris "Best Match" dengan ERA5 setelah tersedia, dan otomatis mundur lebih jauh bila sinkron sempat berhenti lebih dari 10 hari. Jam yang cuacanya kosong dicatat dan dilewati; jam yang lengkap tetap disimpan, lalu ringkasan dicetak. Perintah keluar dengan kode 1 bila ada kota yang gagal diambil. `data/riwayat_online.csv` hanya ditulis dengan `--csv` (di Vercel berkas proyek tidak bisa ditulis).

### Jadwal otomatis (GitHub Actions)

`.github/workflows/sinkron-riwayat.yml` menjalankan `python sinkron_riwayat.py` tiap 3 jam. Workflow hanya membaca repositori dan tidak commit atau push apa pun. Vercel Cron tidak dipakai karena paket Hobby hanya mengizinkan sekali sehari.

1. Di GitHub, buka repositori → **Settings → Secrets and variables → Actions → New repository secret**.
2. Nama `SUPABASE_DB_URL`, nilai URI **Session pooler** Supabase (sama seperti di atas).
3. Buka tab **Actions → Sinkron riwayat per jam → Run workflow** untuk mencoba pertama kali. Centang `penuh` pada eksekusi pertama agar riwayat sejak 1 Oktober 2026 terisi.

GitHub menonaktifkan workflow terjadwal pada repositori publik yang tidak aktif 60 hari; aktifkan lagi dari tab Actions bila itu terjadi. Halaman Riwayat memberi tanda bila data terakhir lebih tua dari 6 jam.

## Deploy ke Vercel

Vercel mengenali `main.py` (instance bernama `app`) sebagai aplikasi FastAPI. `.python-version` menetapkan Python 3.12 dan `vercel.json` mengecualikan `laporan/`, `bukti/`, `desain/`, `data/*.json`, dan berkas yang tidak dibaca aplikasi dari bundel fungsi. `data/cuaca_udara.csv` dan `data/riwayat_online.csv` tetap ikut. [Panduan FastAPI di Vercel](https://vercel.com/docs/frameworks/backend/fastapi)

1. Pastikan Supabase sudah siap (langkah di atas) dan `python penyimpanan.py` pernah berhasil agar tabelnya ada.
2. Di [vercel.com](https://vercel.com), **Add New → Project**, impor repositori ini. Framework terdeteksi otomatis; tidak ada build command.
3. Di **Settings → Environment Variables**, isi untuk Production (dan Preview bila perlu):

   | Nama | Nilai |
   |---|---|
   | `SUPABASE_DB_URL` | URI **Session pooler** Supabase |
   | `SENSOR_TOKEN` | token panjang acak, mis. hasil `secrets.token_urlsafe(32)` |

4. **Deploy**. Periksa `/api/riwayat?kota=Bandung&terbaru=1` dan pastikan `sumber_data` bernilai `Supabase`. Setelah selesai, isi secret `SUPABASE_DB_URL` di GitHub (bagian sebelumnya) dan jalankan workflow sinkron sekali.
5. Arahkan ESP32 atau pengirim lain ke `https://NAMA-PROYEK.vercel.app/pengukuran` dengan header `Authorization: Bearer <SENSOR_TOKEN>`.

Catatan: Vercel menjalankan aplikasi sebagai fungsi serverless, jadi tanpa `SUPABASE_DB_URL` tidak ada penyimpanan sensor permanen. Halaman Sensor dan `POST /pengukuran` lalu menjawab `503` dengan pesan yang jelas, bukan error 500, dan Riwayat memakai salinan CSV di repositori. Prakiraan di-cache lewat header `Cache-Control` (`s-maxage=900`), tidak hanya memori proses. Jangan simpan token atau URI di repositori; `.env` dan `.streamlit/secrets.toml` sudah ada di `.gitignore`.

## Sumber arsip

Arsip berisi data per jam sepanjang 2025. Cuaca berasal dari ECMWF ERA5 dan estimasi PM2.5 dari Copernicus Atmosphere Monitoring Service melalui Open-Meteo. Setiap kota diwakili satu titik model. [Arsip cuaca](https://open-meteo.com/en/docs/historical-weather-api) · [Data kualitas udara](https://open-meteo.com/en/docs/air-quality-api) · [Prakiraan](https://open-meteo.com/en/docs) · [Lisensi CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Pengujian

```powershell
.\.venv\Scripts\python uji.py
.\.venv\Scripts\python -m unittest uji_sensor uji_api
```

`uji.py` memeriksa 26.280 baris tanpa duplikat dan tanpa NaN, mencocokkan 48 nilai indikator (3 kota × 4 periode × 4 variabel) dari `/api/analisis` dengan hitungan Pandas, dan menulis hasilnya ke `bukti/uji_indikator.csv`. `uji_api.py` menguji validasi, fallback riwayat ke CSV, `503` prakiraan, penerima `POST /pengukuran`, serta logika sinkron riwayat (pemotongan rentang ERA5 dan model operasional). Semua tes berjalan tanpa internet dan tanpa database asli.

Untuk memperbarui arsip 2025, cadangkan folder `data`, jalankan `ambil_data.py` lalu `analisis.py` dengan Python dari venv. Keduanya menulis ulang data historis.
