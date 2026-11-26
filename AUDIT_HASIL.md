# AUDIT_HASIL — SmartCity-CuacaKota

Diaudit pada 2026-11-26 terhadap `main` @ `3a248f1` (merge "Gabung perubahan Newten dengan ikon situs"). Mode baca-saja. Berkas yang dibuat hanya ini.

## 0. Asumsi dan cara kerja

- **Keadaan repo berbeda dari sesi sebelumnya.** Merge sudah di-commit (`3a248f1`), pohon kerja bersih. `static/sensor.html` **masih ada** di HEAD (konflik modify/delete diselesaikan dengan mempertahankannya).
- Satu-satunya identitas "nama sama, email beda": `newten90 <newten.24001@…>` (16 commit) dan `Newten Putra <newten24001@…>` (2 commit). Alamat berbeda satu titik, kemungkinan orang yang sama (`DUGAAN`). Commit pemilik repo ini memakai nama `unknown`.
- Tes dan server dijalankan dengan `SUPABASE_DB_URL=""` (diset kosong agar `.env` tidak menimpa; terverifikasi `cloud_url()==''`). Tidak ada koneksi ke database cloud. Venv bersih dibuat di folder scratchpad di luar repo. Server uvicorn (port 8765) sudah dimatikan. `git status` bersih setelah semua pekerjaan.
- Isi `.env` **tidak dibaca**. Percobaan awal saya memuat satu perintah yang menyentuh `.env`; perintah itu ditolak sistem dan **tidak dieksekusi**. Saya hanya memeriksa `git check-ignore` dan riwayat git.
- Berkas `.docx`/`.pdf` laporan **tidak diurai**; klaim laporan dibandingkan dengan teks yang kamu sebutkan di brief dan `laporan/Laporan-Akhir-Telematika.md`.
- Atribusi penulis dari `git blame` **tidak** berarti siapa yang mengerjakan (lihat bagian 2).

## 1. Ringkasan eksekutif

Aplikasi berjalan dan konsisten: 24 tes `uji_api` lulus, `uji.py` lulus, semua endpoint merespons benar, tidak ada rahasia nyata di berkas terlacak maupun riwayat git, SQL diparameterisasi, tidak ada XSS yang ditemukan. Penyimpangan terbesar adalah **fitur sensor IoT (POST /pengukuran) sudah dihapus** padahal laporan minggu 2 dan spesifikasi desain masih mengandalkannya.

| Tingkat | Jumlah |
|---|---|
| Kritis | 0 |
| Tinggi | 2 |
| Sedang | 6 |
| Rendah | 10 |

Tiga risiko terbesar: (1) T-01 fitur sensor dihapus, dokumen dan desain tidak sinkron; (2) T-02 risiko koneksi DB di Vercel/serverless (session pooler, tanpa pembatas) `[DUGAAN]`; (3) S-01 skrip CDN tanpa SRI dan tanpa header keamanan.

## 2. Kontribusi per penulis (faktual)

Total 21 commit (`git log --all`), 1 branch (`main`, sejajar `origin/main`).

| Identitas git | Commit | Tambah / hapus | Berkas unik disentuh | Jenis pekerjaan |
|---|---|---|---|---|
| `Newten Putra` (newten24001@) | 2 | +27.712 / −1 | 18 | Initial commit + upload awal: data (JSON/CSV 26.280 baris), `ambil_data.py`, `analisis.py`, bukti |
| `newten90` (newten.24001@) | 16 | +9.354 / −5.213 | 40 | Fitur sensor, Supabase, dashboard Streamlit lalu penyesuaian, laporan Word/PDF, sinkron data riwayat, penghapusan sensor (`7c4f969`) |
| `unknown` (sebastianagustinolie@) | 3 | +3.091 / −353 | 53 | `98f15a2` "page dashboard" (migrasi ke FastAPI + HTML/JS, desain, workflow), `3054e15` ikon situs, `3a248f1` merge |

Penanda khusus:
- **Commit sangat besar:** `c650b71` (+27.711, data mentah), `98f15a2` (46 berkas, +3.038/−353, migrasi total), `61946bf` dan `10f853b` (ganti ±3.500 baris CSV riwayat), `53343b4` (+3.795, data).
- **Commit murni data:** `61946bf`, `10f853b` (hanya `data/riwayat_online.csv`).
- **Ditambah lalu dihapus:** `app.py`, `cuaca_online.py`, `tampilan_cuaca.py` (Streamlit, dihapus di `98f15a2`); `prediksi.py`, `laporan/gambar/03-model.png`, `07-simulasi.png` (dihapus di `bfc3326`); `.streamlit/*` (`de0fca0`); `sensor.py`, `static/js/sensor.js`, `static/sensor.html` *(dihapus di `7c4f969`, tetapi `sensor.html` kembali lewat merge)*, `uji_sensor.py`.
- Tidak ada commit yang murni format/rename.

**Blame HEAD (jumlah baris per identitas):** `main.py` 105 unknown / 1 newten90; `layanan.py` 315 / 28; `kondisi.py`, `prakiraan.py` 100% unknown; `analisis.py` 29 Newten Putra / 10 unknown; `penyimpanan.py` 39 newten90; `sinkron_riwayat.py` 163 / 5; `uji_api.py` 370 / 28; `uji.py` 31 unknown / 14 Newten Putra / 1 newten90; `static/js/*`, `static/css/*`, `static/*.html` hampir seluruhnya unknown (tambahan newten90: `cuaca.js` 9, `riwayat.js` 38 baris). Catatan: sebagian kode migrasi dibuat dengan bantuan AI atas permintaan pemilik repo, sehingga "penulis commit" tidak sama dengan "pengerja".

## 3. Temuan

### Tinggi

**T-01 — Fitur sensor IoT dan `POST /pengukuran` sudah dihapus; dokumen dan desain tidak sinkron** `[TERVERIFIKASI]`
- Bukti: `git show --stat 7c4f969` menghapus `sensor.py`, `static/js/sensor.js`, `static/sensor.html`, `uji_sensor.py`; `main.py` HEAD tidak punya route `/pengukuran` (`curl -X POST /pengukuran` → 404 `{"pesan":"Alamat tidak ditemukan."}`); `/sensor` → 404.
- Dampak: klaim "sensor lewat POST /pengukuran", "5 halaman", dan "31 tes lulus" dalam laporan minggu 2 tidak lagi benar untuk HEAD (30 tes `uji_api` + 1 `uji_sensor` di `3054e15` → 24 tes di HEAD). `desain/README.md:23,41,58–64,76` dan `desain/referensi/*sensor*.html` masih mendeskripsikan halaman Sensor dan `sensor.py`. Jika penilaian tugas Telematika mensyaratkan komponen sensor/IoT, ini celah fungsional.
- Saran: putuskan eksplisit. Jika sensor dibuang, perbarui laporan dan `desain/`. Jika dibutuhkan, pulihkan dari `3054e15`.

**T-02 — Risiko koneksi database di serverless Vercel dan batas waktu** `[DUGAAN]`
- Berkas: `penyimpanan.py:13`, `README.md` bagian Supabase/Vercel, `prakiraan.py:15`.
- Bukti: koneksi Postgres dibuka per permintaan (`psycopg.connect(..., connect_timeout=5)`); README menyuruh memakai **Session pooler** (port 5432), yang membatasi jumlah klien serentak. Cache 15 menit hanya per instance (`layanan._CACHE`, memori proses). `urlopen(..., timeout=15)` ke Open-Meteo bisa melebihi batas durasi fungsi plan gratis.
- Dampak: bila banyak instance serverless dingin, koneksi bisa habis atau permintaan timeout; aplikasi jatuh ke CSV (terlabel) sehingga fungsional, tetapi tidak sengaja "tidak terhubung".
- Saran: uji sekali di Vercel; pertimbangkan transaction pooler (port 6543) dan `maxDuration`. Tidak bisa saya buktikan tanpa akses Vercel.

### Sedang

**S-01 — Plotly dan Google Fonts dimuat dari CDN tanpa SRI; tidak ada header keamanan** `[TERVERIFIKASI]`
- `static/analisis.html:17`, `static/riwayat.html:17` (`<script defer src="https://cdn.plot.ly/plotly-basic-3.0.1.min.js">` tanpa `integrity`/`crossorigin`). `curl -i /api/kota` hanya mengembalikan `date, server, cache-control, content-length, content-type`: tidak ada `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`.
- Dampak: kompromi CDN = eksekusi skrip di origin; clickjacking mungkin.
- Saran: tambahkan `integrity`, atau muat berkas Plotly dari `static/`; tambahkan middleware header sederhana.

**S-02 — Kegagalan database ditelan tanpa log** `[TERVERIFIKASI]`
- `layanan.py:246` `except DB_ERRORS: pass`; `DB_ERRORS` (`penyimpanan.py:11`) mencakup `ValueError` dan `OSError`, sehingga bug biasa ikut tersembunyi. Tidak ada `logging` di seluruh repo.
- Dampak: Supabase down atau salah konfigurasi hanya terlihat sebagai label "Supabase tidak terjangkau" di UI; tidak ada jejak sebab. Hasil gagal di-cache 60 detik.
- Saran: `logging.exception` (tanpa mencetak URI) dan persempit tipe pengecualian.

**S-03 — Pesan salah bila tabel Supabase kosong** `[TERVERIFIKASI] (dari kode)`
- `layanan.py:238-250` dan `294-296`: jika koneksi berhasil tetapi `rows` kosong, kode jatuh ke CSV dan memberi catatan "Supabase tidak terjangkau", padahal koneksi sehat. Menyesatkan saat awal setup.

**S-04 — Tidak ada CI untuk tes; tes tidak mencakup bagian kritis** `[TERVERIFIKASI]`
- `.github/workflows/` hanya berisi `sinkron-riwayat.yml`. Tidak ada tes untuk: `penyimpanan.initialize_cloud` dan SQL nyata, `kondisi.py` (hanya lewat `ringkasan`), JavaScript (0 tes), format Indonesia `angka()` Python (tidak ada tes langsung), `main` terhadap Vercel.
- Cakupan baik: `uji_api.py` (24 tes: validasi 400/404, 503 saat prakiraan gagal, fallback CSV, usang, `sinkron` dengan mock, `muat_env`), `uji.py` (48 indikator vs Pandas).

**S-05 — Endpoint analisis mahal dapat dibebani lewat variasi parameter** `[DUGAAN]`
- `/api/analisis` dan `.csv`: ±365² kombinasi `dari/sampai` tiap kota, masing-masing memproses DataFrame dengan `groupby`. `s-maxage=86400` membantu di CDN tetapi variasi parameter menembus cache. Tidak ada batas laju.
- Saran: batasi dengan CDN/Vercel firewall; opsional memoisasi per `(kota,dari,sampai)`.

**S-06 — `static/sensor.html` yatim masih dilayani** `[TERVERIFIKASI]`
- `curl /static/sensor.html` → 200; halaman memuat `/static/js/sensor.js` yang 404, sehingga sekadar `#app` kosong. Juga CSS sisa `static/css/app.css:127` ("halaman Sensor").
- Saran: `git rm static/sensor.html` bila sensor memang dibuang.

### Rendah

- **R-01** `terbaru=abc` → **422** dengan format `{"detail":[...]}` (bawaan FastAPI), bukan `{"pesan":...}` (`main.py:63-69`, `curl "/api/riwayat?terbaru=abc"`). Klien menampilkan "Permintaan gagal (422)". `[TERVERIFIKASI]`
- **R-02** `kondisi.py:2` menyebut `static/js/ikon.js` yang tidak ada (ikon ada di `static/js/util.js`). `[TERVERIFIKASI]`
- **R-03** Kode cuaca 56, 57, 66, 67, 71–77, 85, 86 tidak dipetakan → "Kondisi belum tersedia" (`kondisi.py`; dihitung lewat `condition()`). Jarang relevan di Indonesia. `[TERVERIFIKASI]`
- **R-04** `static/js/riwayat.js:139`: `pasang()` dipanggil ulang setiap "Tampilkan jam lagi" sehingga pendengar klik pada chip variabel menumpuk (tiap klik chip menggambar ulang grafik berkali-kali). `[TERVERIFIKASI] (dari kode)`
- **R-05** Grafik Plotly tidak di-`purge` saat ganti kota; pendengar resize dapat menumpuk. `[DUGAAN]`
- **R-06** `static/js/cuaca.js:274-276`: bila semua `min/maks` tujuh hari null, `Math.min()` menghasilkan `Infinity`, rentang NaN. `[DUGAAN]` (kasus tepi)
- **R-07** Aksesibilitas: tidak ada *skip link*; satu aturan `:focus-visible` global; `aria-live="polite"` pada seluruh `#halaman` bisa berisik. Kelebihan: `aria-current`, `aria-pressed`, `role=img` + label pada grafik, `prefers-reduced-motion`. `[TERVERIFIKASI]`
- **R-08** Manifest: `purpose: "any maskable"` digabung pada ikon 512; `theme_color` manifest (#2459D6) beda dari `<meta theme-color>` (#EEF3F8). `[TERVERIFIKASI]`
- **R-09** Workflow memakai `actions/checkout@v4`, `setup-python@v5` (tag, bukan SHA). `permissions: contents: read` sudah benar. `[TERVERIFIKASI]`
- **R-10** Atribusi: footer menulis "CAMS via Open-Meteo, CC BY 4.0" tetapi tidak memuat pernyataan Copernicus baku ("Contains modified Copernicus Atmosphere Monitoring Service information"). `[DUGAAN]` soal ketentuan lisensi; periksa teks lisensi resmi. Tidak ada AQI dihitung: yang ditampilkan PM2.5 mentah (µg/m³), jadi "perhitungan AQI" tidak ada di kode.

## 4. Hasil tes dan panggilan endpoint

Perintah dijalankan dari venv bersih (`pandas 2.2.3, numpy 2.5.5, fastapi 0.165.0, starlette 1.10.0, uvicorn 0.54.0, httpx 0.28.1, psycopg 3.3.9`), `SUPABASE_DB_URL=""`.

| Perintah | Hasil |
|---|---|
| `python -m unittest uji_api` | **24 tes, OK** (hanya DeprecationWarning NumPy di `uji_api.py:261`) |
| `python -m unittest uji_api uji_sensor` | 25 tes, **1 error**: `uji_sensor` tidak ada (dihapus di `7c4f969`). Bukan bug; perintah perlu diganti. |
| `python uji.py` | **Lulus** ("48 nilai indikator, data hujan kosong"); `git status` tetap bersih, jadi `bukti/uji_indikator.csv` tidak berubah |
| `python -m pip_audit -r requirements.txt` | "No known vulnerabilities found" |
| `node --check static/js/*.js` | tanpa galat sintaks (6 berkas) |

Pemanggilan `uvicorn main:app --port 8765` (internet ke Open-Meteo tersedia):

| Permintaan | Status | Catatan |
|---|---|---|
| `GET /api/kota` | 200 | 3 kota + koordinat, `s-maxage=86400` |
| `GET /api/cuaca?kota=Bandung` | 200 (5.133 B) | `s-maxage=900`, sesuai README |
| `GET /api/cuaca?kota=Medan` | 400 | `{"pesan":"Kota tidak dikenal…"}` |
| `GET /api/riwayat?kota=Jakarta&terbaru=2` | 200 | sumber = salinan CSV, `usang:true`, `selisih_jam 14.7`, catatan "SUPABASE_DB_URL kosong" |
| `GET /api/riwayat?terbaru=0` | 400 | pesan 1–10000 |
| `GET /api/riwayat?terbaru=abc` | **422** | format `detail` (R-01) |
| `GET /api/riwayat.csv?kota=Surabaya` | 200 | `Content-Disposition: attachment`, `no-store` |
| `GET /api/analisis?kota=Bandung&dari=2025-01-01&sampai=2025-01-31` | 200 | 744 jam, hujan 460,6 mm |
| `GET /api/analisis?dari=2025-02-01` | 400 | minta tanggal akhir |
| `GET /api/analisis?dari=2024-01-01&sampai=2025-01-01` | 400 | di luar 2025 |
| `GET /api/analisis.csv?...` | 200 | CSV attachment |
| `GET /`, `/analisis`, `/riwayat`, `/kota` | 200 | `max-age=0, must-revalidate` |
| `GET /sensor`, `/pengukuran`, `POST /api/pengukuran`, `/docs` | 404 | JSON 404 |
| `GET /favicon.ico` | 200 (5.643 B) | `image/x-icon`, `max-age=86400` |
| `GET /static/icons/manifest.webmanifest` | 200 | `application/manifest+json` |
| `GET /static/sensor.html` | 200 | yatim (S-06) |
| `GET /static/../main.py`, `/static/%2e%2e/main.py` | 404 | tidak ada traversal |
| `Origin: http://evil.example` | tanpa header CORS | tidak ada CORS (baik) |

Logika yang saya uji sendiri:
- Pearson: `a=[1,2,3,4,5]`, `b=[2,4,5,4,5]` → `analisis.pearson` = 0,774597 = hitung manual (Σ(x−x̄)(y−ȳ)/√(Σ(x−x̄)²Σ(y−ȳ)²)). Varian nol atau n=1 → `None` (sesuai desain).
- Hujan tahunan Bandung: jumlah baris `rain` = 4.270,0 = jumlah di `harian.csv` (hujan dijumlah, bukan dirata-rata). 36 dari 36 kota-bulan "bulan_utuh".
- Format angka `1.234,50`, `−0,00` dinormalisasi jadi `0,00`.
- Zona waktu: seluruh waktu WIB naif; `pola_jam` menggeser `DateOffset(years=1)` konsisten (tidak ada 29 Februari di rentang).

## 5. Kesesuaian klaim laporan

| Klaim (laporan minggu 2 / brief) | Hasil | Cocok |
|---|---|---|
| FastAPI + HTML/JS + Plotly | `main.py`, `static/*`, Plotly 3.0.1 CDN | Ya |
| 3 kota | Bandung, Jakarta, Surabaya (`ambil_data.py:10`) | Ya |
| 26.280 baris (3×8.760) | 26.280; 8.760/kota; 2025-01-01 00:00 → 2025-12-31 23:00; 0 duplikat, 0 NaN; rentang wajar (suhu 18,2–34,5; RH 41–100; hujan 0–18,1; PM2,5 5,1–275,7) | Ya |
| Riwayat Supabase 3.528 baris | Tidak bisa diperiksa. Salinan CSV kini 4.026 baris (1.342/kota, 2026-10-01 → 2026-11-25 21:00, 0 duplikat, 0 NaN, 0 jam hilang). 3.528 = 49 hari × 24 × 3, konsisten dengan sinkron s.d. 18 Nov | Tidak terverifikasi |
| Sensor via `POST /pengukuran` | Dihapus di `7c4f969`; 404 | **Tidak** (T-01) |
| Sinkron GitHub Actions tiap 3 jam | `cron: "17 */3 * * *"` (UTC) | Ya |
| 31 tes lulus | HEAD: 24 tes `uji_api` (+ `uji.py`). 31 = 30 + 1 pada `3054e15` | **Tidak** untuk HEAD |
| 5 halaman | 4 halaman (Cuaca, Analisis, Riwayat, Kota); Sensor dihapus | **Tidak** |
| README: prakiraan ≤ tiap 15 menit | `s-maxage=900` | Ya |
| README: Streamlit dihapus | tidak ada import/berkas Streamlit; `.streamlit/` kosong; sisa hanya `.gitignore:5`, `vercel.json` exclude, `desain/*` (sejarah) | Ya (sisa kosmetik) |

## 6. Yang sudah baik

- **Tanpa rahasia nyata:** `git grep` pada seluruh revisi (`git rev-list --all`) untuk URI `postgres://…@`, token, kunci hanya menemukan placeholder (`PROJECT_REF:PASSWORD@POOLER_HOST`, `pengguna:rahasia@tidak-ada.invalid`). `.env` di-gitignore (`.gitignore:4`) dan **tidak pernah ditambahkan** ke riwayat. `.streamlit/secrets.example.toml` di riwayat hanya berisi komentar dan placeholder.
- **SQL aman:** semua kueri konstanta atau `executemany` berparameter; tidak ada input pengguna yang masuk ke SQL (`sinkron_riwayat.py:27,129`). RLS aktif dan `REVOKE ALL … FROM PUBLIC, anon, authenticated` (`supabase.sql:13-14`).
- **Sinkron tahan gagal:** pengambilan paralel dulu, penulisan dalam satu transaksi (`with session()` + `executemany`), `ON CONFLICT (kota,waktu) DO UPDATE` (idempoten), jam kosong dilewati, kegagalan satu kota tetap menyimpan kota lain lalu `exit 1`, `concurrency` mencegah balapan, `timeout-minutes: 15`.
- **Tidak ada penulisan filesystem saat runtime** (kecuali `--csv` dari laptop, atomik via berkas sementara) sehingga aman untuk Vercel read-only.
- **Frontend:** seluruh teks dari API lewat `esc()` (`util.js:37`); `kota` divalidasi daftar putih (`shell.js:146`); `dari/sampai` di-escape; token versi `versi/nomor` mencegah respons basi menimpa halaman; Plotly punya fallback bila CDN gagal; angka dan tanggal memakai `id-ID` tanpa konversi zona waktu peramban.
- **Dependensi dipin** (`fastapi==0.165.0`, `pandas==2.2.3`, …); `pip-audit` bersih; docs/openapi dimatikan (`main.py:22`); tidak ada CORS terbuka; `Cache-Control` per endpoint masuk akal.
- **Desain:** `desain/tokens.css` ≈ `static/css/tokens.css` (selisih: font via `<link>` bukan `@import`, plus `--info-bg/--info-fg/--row-hi`); rail 96 px, breakpoint 900/480 px, atribusi footer, favicon, `apple-touch-icon`, manifest, dan `/favicon.ico` semuanya ada dan melayani 200.

## 7. Tidak bisa diverifikasi

- Isi dan jumlah baris tabel `public.cuaca_online` di Supabase (tanpa kredensial; sengaja tidak disambungkan).
- Perilaku nyata di Vercel (ukuran bundel di server, batas durasi fungsi, penyajian `/static` oleh fungsi FastAPI, `excludeFiles`). Ukuran lokal: `data/` 3,7 MB (termasuk `*.json` yang dikecualikan), `static/` 209 KB; tidak ada `.vercelignore`.
- Status GitHub Actions: apakah secret `SUPABASE_DB_URL` terisi dan workflow benar-benar berjalan sukses.
- Syarat lisensi/penggunaan Open-Meteo (tier gratis non-komersial), Supabase free tier (project dijeda saat tidak aktif) dan Copernicus: dari ingatan, bukan dari dokumen resmi yang saya baca sekarang.
- Isi `.docx`/`.pdf` laporan minggu 2 dan 3 (tidak diurai); render visual halaman di peramban (kontras, tampilan HP) tidak diuji di browser.
- Dua masalah kecil yang kamu sebut: **font serif pada "78%"** dan **judul "Tren 1 pembacaan terakhir"** berada di halaman Sensor. Di kode aktif sudah tidak ada (`sensor.js` dihapus; `git grep "pembacaan"` kosong). Di berkas referensi `desain/referensi/desktop-sensor.html` teks SVG memakai `font-family="Manrope"` tanpa fallback generik, sehingga bila font belum termuat peramban memakai serif `[TERVERIFIKASI] (di referensi)`; judulnya di referensi tertulis "Tren 1 jam". Status di sebuah build sensor yang berjalan tidak bisa dicek.
- Perilaku HEAD/OPTIONS pada halaman (hanya GET didaftarkan, `main.py:100`; kemungkinan 405 untuk HEAD) `[DUGAAN]`.

## 8. Perbaikan berurutan prioritas

**Wajib sebelum deploy Vercel**
1. Putuskan nasib sensor (T-01): hapus `static/sensor.html` + CSS sisa, atau pulihkan fiturnya. Samakan laporan, README, `desain/README.md`.
2. Pastikan di Vercel hanya `SUPABASE_DB_URL` yang wajib (tidak ada `SENSOR_TOKEN` lagi); uji `/api/riwayat?kota=Bandung&terbaru=1` dan cek `sumber_data=="Supabase"`. Pertimbangkan transaction pooler dan `maxDuration` (T-02).
3. Tambahkan `integrity` pada Plotly atau salin ke `static/`; tambahkan header keamanan (S-01).
4. Tambahkan logging pada kegagalan DB dan perbaiki pesan "tabel kosong" (S-02, S-03).

**Setelah itu**
5. Samakan format galat 422 → `{"pesan":...}` (R-01).
6. Ganti perintah tes (hapus `uji_sensor`), tambah workflow CI yang menjalankan `unittest uji_api` dan `uji.py` (S-04).
7. Perbaiki `pasang()` ganda di `riwayat.js`, purge Plotly (R-04, R-05).
8. Rapikan: komentar `kondisi.py`, kode cuaca yang belum dipetakan, atribusi Copernicus, manifest, SHA action (R-02, R-03, R-08, R-09, R-10).
9. Pertimbangkan batas laju/CDN untuk `/api/analisis` (S-05).
