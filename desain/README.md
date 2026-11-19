# Desain Cuaca Kota (tanpa Streamlit)

Folder ini adalah acuan tampilan untuk migrasi dashboard dari Streamlit ke web biasa.
Desain yang dipilih adalah **arah E: gaya aplikasi HP yang dipakai juga di desktop**.

Kanvas desain lengkap (semua arah, bisa dikomentari): https://claude.ai/artifact/ChBdCTJmRRL2YgAPxJYZrD

## Isi folder

| Berkas | Fungsi |
|---|---|
| `referensi/desktop-*.html` | Tampilan desktop per halaman. Buka langsung di browser. |
| `referensi/hp-*.html` | Tampilan HP (390 px) untuk acuan responsif. |
| `referensi/state-kosong-gagal.html` | Isi pesan untuk kondisi gagal, kosong, dan memuat (gayanya ikut arah E saat diimplementasikan). |
| `tokens.css` | Warna, huruf, radius, dan jarak. |
| `PROMPT_MIGRASI.md` | Prompt untuk Claude Code. |

Semua angka prakiraan, bentuk grafik, dan data sensor di berkas referensi adalah **contoh**. Angka ringkasan 2025 (suhu rata-rata, total hujan, bulan terbasah/terkering, korelasi) berasal dari laporan minggu 2. Aplikasi asli harus mengambil semua angka dari data.

## Kerangka halaman

- Lebar isi maksimal 1440 px, padding 24 px, latar `--bg`.
- **Rail navigasi** di kiri (96 px): logo kotak gradien, lalu 5 item ikon + label: Cuaca, Analisis, Riwayat, Sensor, Kota. Item aktif berlatar `--accent-soft` dan berwarna `--accent`.
- **Bar atas** di area isi: judul halaman (h1) + subjudul di kiri, tombol kota Bandung / Jakarta / Surabaya di kanan. Kota terpilih tetap sama saat pindah halaman (simpan di query `?kota=` dan/atau localStorage).
- Di bawah ±900 px, rail pindah ke bawah sebagai tab bar seperti `referensi/hp-*.html`. Kartu yang berjajar turun jadi satu kolom, dan tabel lebar digulir di dalam kotaknya sendiri.
- Footer kecil berisi atribusi: Open-Meteo, ERA5 (ECMWF), CAMS, lisensi CC BY 4.0.
- Ikon garis (stroke 1.8), tanpa emoji. Bentuk ikon ada di berkas referensi sebagai SVG inline.

## Halaman dan sumber datanya

### 1. Cuaca (`desktop-cuaca.html`)
| Komponen | Data | Sumber di repo |
|---|---|---|
| Hero gradien: suhu, kondisi, terasa, min/maks, jam data | `current.temperature_2m`, `apparent_temperature`, `weather_code`, `daily.temperature_2m_min/max` hari ini | `cuaca_online.outlook()` |
| Kartu kelembapan, angin | `current.relative_humidity_2m`, `wind_speed_10m` | `outlook()` |
| Kartu PM2.5 "jam lalu" | baris terakhir `pm2_5` kota itu | `cuaca_online` di Supabase, cadangan `data/riwayat_online.csv` |
| Kartu terbit/terbenam | `daily.sunrise/sunset` hari ini | `outlook()` |
| Tips hujan | jam dengan `precipitation_probability` tertinggi di 12 jam ke depan. Tampilkan hanya jika ≥ 50%. | `outlook()` |
| Per jam (24 jam, digeser) | `hourly.temperature_2m`, `precipitation_probability`, `weather_code` | `outlook()` |
| 7 hari | `daily` 7 tanggal setelah hari ini: kondisi, min/maks, peluang hujan, presipitasi | `outlook()` |
| Ringkasan sensor | pengukuran terakhir kota itu + suhu model di jam yang sama | `Store.devices()`, `Store.history()`, `cuaca_online` |

Kode WMO → teks memakai tabel `CONDITIONS` yang sudah ada di `tampilan_cuaca.py`, dengan ikon garis sebagai pengganti emoji. Prakiraan di-cache 15 menit (sama dengan `ttl=900` sekarang).

### 2. Analisis 2025 (`desktop-analisis.html`)
- Pemilih rentang tanggal (01/01–31/12/2025, inklusif) + tombol cepat **Setahun, Jan–Mar, Jun–Sep, Desember**, dan tombol Unduh CSV.
- 4 kartu: rerata suhu, total hujan, bulan terbasah, bulan terkering. Logikanya harus sama dengan `analisis.aggregate()` dan `monthly()`: hujan hanya dijumlahkan bila semua jam punya nilai, dan korelasi bulanan hanya memakai bulan utuh.
- Kartu temuan: kalimat dari angka nyata, jangan ditulis manual di kode.
- Grafik garis suhu harian, batang hujan per bulan (bulan terkering diberi warna `--warm`), batang PM2.5 per bulan (`--pm`, label "estimasi CAMS, bukan sensor").
- Tabel tiga kota untuk periode yang sama, ditambah kotak catatan korelasi (teks di referensi).
- Bila ada: grafik sebaran suhu–kelembapan dan hujan–PM2.5, dengan teks `r = … · n pasangan` atau "Korelasi belum tersedia · n pasangan" seperti `correlation()` di `app.py`.

### 3. Riwayat per jam (`desktop-riwayat.html`)
- Kartu sumber: "Supabase · public.cuaca_online" atau "salinan impor di repositori", jumlah jam, rentang waktu, dan tombol unduh.
- Grafik per jam dengan pilihan variabel (Suhu, Kelembapan, Presipitasi, Angin, PM2.5). Bagian yang `sumber`-nya model operasional diberi area `--accent-soft` dan garis putus-putus.
- Tabel terbaru di atas: waktu WIB, suhu, kelembapan, presipitasi, angin, kode WMO, PM2.5, sumber.

### 4. Sensor IoT (`desktop-sensor.html`)
- Pembacaan terakhir besar + lingkaran kelembapan, status Aktif bila kiriman terakhir < 15 menit.
- Perbandingan dengan model jam yang sama, selisih ditandai `--warm`.
- Tren (suhu & kelembapan) dari 60 baris `Store.history()`.
- Daftar perangkat dari `Store.devices()`.
- Tabel kiriman + kotak arti kode 201/200/400/401/409/503. Sensor tidak menyimpan kode balasan, jadi kolom status pada tabel cukup "Tersimpan".
- Penerima `sensor.py` **tidak diubah**.

### 5. Pilih kota (`desktop-kota.html`)
Tiga kartu kota (kota terpilih bergradien) berisi suhu sekarang, kondisi, rerata suhu 2025, dan hujan 2025. Klik kartu berarti pilih kota lalu kembali ke Cuaca.

## Kondisi gagal, kosong, memuat
Teks pesan ikut kode yang sekarang:
- Prakiraan gagal: "Prakiraan Open-Meteo sedang tidak tersedia. Riwayat per jam tersedia di bawah." + tombol Coba lagi.
- Supabase gagal: pakai `data/riwayat_online.csv` dan tampilkan label sumber "salinan impor di repositori".
- Rentang belum lengkap: "Pilih tanggal akhir untuk menghitung ringkasan."
- Bulan parsial: "Bulan parsial atau hujan tidak lengkap: … Grafik memakai tanggal terpilih. Korelasi bulanan hanya memakai bulan utuh."
- Hujan tidak lengkap: tampilkan "—".
- Belum ada sensor: "Belum ada pengukuran" + petunjuk menjalankan `sensor.py`.
- Memuat: kerangka abu-abu (skeleton), bukan spinner.
Gaya visualnya pakai token arah E (kartu putih, `--note-bg` untuk peringatan).

## Aksesibilitas
Tombol dan link berupa elemen asli (`<button>`, `<a>`, `<label>` + `<input>`), tinggi minimal 44 px, kontras teks ≥ 4.5:1, grafik diberi `aria-label`, dan warna tidak menjadi satu-satunya pembeda (selalu ada label teks).
