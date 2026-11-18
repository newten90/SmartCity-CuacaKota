# Cuaca Kota

Cuaca Kota dibuka dengan cuaca Bandung saat ini. Pilih Jakarta atau Surabaya untuk melihat kota lain. Semua jam memakai WIB.

Laporan akhir memuat data tiga kota, tangkapan layar, hasil pengujian, dan alur demo tujuh menit. [Unduh laporan Word](https://github.com/newten90/SmartCity-CuacaKota/raw/refs/heads/main/laporan/Laporan-Akhir-Telematika.docx) · [Baca laporan](laporan/Laporan-Akhir-Telematika.md) · [Unduh PDF](laporan/Laporan-Akhir-Telematika.pdf)

![Halaman cuaca Bandung](laporan/gambar/01-cuaca.png)

Tab **Cuaca & prakiraan** menampilkan kondisi kota saat ini, suhu terasa, kelembapan, angin, waktu terbit dan terbenam matahari, serta prakiraan per jam. Geser deretan jam untuk melihat 24 jam berikutnya. Tabel tujuh hari memperlihatkan kondisi, rentang suhu, kemungkinan hujan, jumlah presipitasi, dan angin maksimum per hari. Angka berasal dari prakiraan operasional Open-Meteo dan diperbarui paling sering setiap 15 menit saat dashboard dibuka. [Weather Forecast API](https://open-meteo.com/en/docs)

Di bawah prakiraan ada riwayat per jam yang bisa diunduh sejak **1 Oktober 2026**. Riwayat ini menyimpan data grid meteorologi untuk titik koordinat tiap kota. Data perangkat IoT tetap berada di tabel tersendiri.

Tab **Analisis 2025** menampilkan suhu, kelembapan, total hujan, dan estimasi PM2.5 menurut kota dan rentang tanggal.

## Menjalankan dashboard

Dari folder proyek, jalankan di PowerShell dengan Python 3.12 atau 3.13.

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Buka alamat lokal yang muncul di terminal. Arsip analisis dan salinan riwayat per jam sudah tersedia di folder `data`. Cuaca terkini membutuhkan internet.

## Hubungkan ke Supabase

1. Buat proyek di [Supabase Dashboard](https://supabase.com/dashboard). Simpan **database password** yang kamu buat. Setelah proyek siap, buka **Connect**, pilih **Session pooler**, dan salin URI PostgreSQL-nya. [Panduan koneksi Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)
2. Buka `.streamlit/secrets.toml` di folder proyek. Untuk clone baru, salin dulu `.streamlit/secrets.example.toml` menjadi `.streamlit/secrets.toml`. Isi baris berikut dengan URI proyekmu. Ganti placeholder password di URI dengan database password. Karakter khusus pada bagian password perlu ditulis dalam format URL, misalnya `@` menjadi `%40`.

   ```toml
   SUPABASE_DB_URL = "postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres"
   ```

3. Setelah menginstal dependensi, jalankan perintah berikut dari folder proyek. Perintah ini membuat tabel `public.cuaca_sensor` dan mengecek apakah tabel bisa dibaca. Setup bisa diulang.

   ```powershell
   .\.venv\Scripts\python penyimpanan.py
   ```

4. Jalankan kembali dashboard dan penerima sensor. Coba kirim satu pengukuran dengan contoh di bawah, lalu buka **Table Editor → cuaca_sensor** untuk melihat baris yang sama di cloud.

Untuk Streamlit Community Cloud, isi `SUPABASE_DB_URL` yang sama di pengaturan **Secrets** aplikasi. Penerima tetap harus berjalan di mesin yang bisa dihubungi sensor dan punya akses internet ke Supabase. Simpan URI hanya pada penerima dan server Streamlit. ESP32 cukup memakai token penerima. [Pengaturan secrets Streamlit](https://docs.streamlit.io/develop/concepts/connections/secrets-management)

Dengan URI kosong, demo memakai SQLite di `data/sensor.sqlite3`. Setelah URI diisi, kiriman baru dan pembacaan dashboard memakai Supabase. Riwayat lama tetap berada di SQLite. Jika cloud sedang bermasalah, penerima mengembalikan 503 agar perangkat bisa mencoba lagi dengan waktu pengukuran yang sama.

## Kirim data sensor

Buka terminal PowerShell kedua di folder yang sama. Buat token untuk sesi ini, lalu nyalakan penerima.

```powershell
$env:SENSOR_TOKEN = .\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:SENSOR_TOKEN  # Salin nilainya untuk terminal pengirim.
.\.venv\Scripts\python sensor.py
```

Untuk mencoba dari laptop, buka PowerShell **ketiga**. Isi token yang sama. Kirim satu contoh pengukuran berikut.

```powershell
$token = Read-Host 'Token penerima'
$body = @{
    sensor = 'demo-laptop'
    kota = 'Bandung'
    waktu = [DateTimeOffset]::Now.ToString('o')
    suhu = 26.4
    kelembapan = 78
} | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://127.0.0.1:8765/pengukuran' `
    -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json' -Body $body
```

Kode 201 berarti pengukuran tersimpan. Di Supabase, buka **Table Editor → cuaca_sensor** dan segarkan tabel untuk melihat nama perangkat, waktu, suhu, dan kelembapannya. Ulangi blok mulai dari `$body` dengan suhu berbeda untuk melihat pembaruan. Jika kota, nama sensor, dan waktunya sama, kiriman ulang mendapat 200. Jika nilainya berbeda untuk pengukuran yang sama, penerima mengembalikan 409.

Untuk ESP32 atau pengirim lain di Wi-Fi yang sama, jalankan `sensor.py --host 0.0.0.0` dengan Python dari venv. Gunakan alamat IPv4 laptop sebagai pengganti `127.0.0.1`. Perangkat mengirim HTTP POST ke `/pengukuran` dengan header dan kolom JSON yang sama. Isi `waktu` dengan waktu pengukuran beserta zona waktunya, misalnya `2026-11-18T08:30:00+07:00`. Gunakan jaringan lokal tepercaya untuk HTTP ini.

## Perbarui riwayat tiga kota

Jalankan `.\.venv\Scripts\python cuaca_online.py` dari folder proyek dengan koneksi Supabase aktif. Perintah mengambil riwayat sejak 1 Oktober 2026 sampai jam berjalan dalam WIB, lalu memperbarui tabel `public.cuaca_online`. Pasangan kota dan waktu hanya mendapat satu baris meski impor diulang. Salinan CSV di `data/riwayat_online.csv` dipakai dashboard saat database belum tersedia. Setiap baris menyimpan sumber cuaca; arsip memakai ERA5, sedangkan tujuh tanggal terkini memakai model operasional. PM2.5 berasal dari CAMS melalui Open-Meteo. Impor ini dijalankan terpisah dari pembaruan prakiraan di dashboard.

## Sumber arsip

Arsip berisi data per jam sepanjang 2025. Cuaca berasal dari ECMWF ERA5 dan estimasi PM2.5 dari Copernicus Atmosphere Monitoring Service melalui Open-Meteo. Setiap kota diwakili satu titik model. [Arsip cuaca](https://open-meteo.com/en/docs/historical-weather-api) · [Data kualitas udara](https://open-meteo.com/en/docs/air-quality-api) · [Lisensi CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Pengujian

```powershell
.\.venv\Scripts\python uji.py
.\.venv\Scripts\python -m unittest uji_sensor
```

Untuk memperbarui arsip, cadangkan folder `data`, jalankan `ambil_data.py` lalu `analisis.py` dengan Python dari venv. Keduanya menulis ulang data historis.
