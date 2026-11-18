# Cuaca Kota

Cuaca Kota menampilkan cuaca dan kualitas udara Bandung, Jakarta, dan Surabaya. Di tab **Analisis 2025**, pilih kota dan rentang tanggal untuk melihat suhu, kelembapan, total hujan, dan PM2.5. Grafik dan unduhan CSV mengikuti tanggal yang dipilih. Untuk membandingkan hujan dan PM2.5 antarbulan, aplikasi hanya memakai bulan dengan data lengkap.

Di tab **Prediksi suhu**, langsung terlihat perkiraan suhu rata-rata untuk besok sampai tujuh hari ke depan. Pilih Bandung, Jakarta, atau Surabaya untuk berpindah kota. Tanggal mengikuti WIB. Kalau sudah ada cukup pengukuran dari kemarin, model ikut memperhitungkannya.

Tab **Sensor langsung** menunjukkan waktu, suhu, dan kelembapan terakhir yang dikirim tiap perangkat. Tab **Simulasi sensor** memutar ulang data Bandung pada 1 Januari 2025, satu jam per klik.

## Menjalankan dashboard

Dari folder proyek, jalankan di PowerShell dengan Python 3.12 atau 3.13.

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Buka alamat lokal yang muncul di terminal. Analisis dan simulasi langsung bisa dipakai karena arsip 2025 sudah ada di folder `data`.

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

4. Jalankan kembali dashboard dan penerima sensor. Cek tulisan **Penyimpanan · Supabase** di tab **Sensor langsung**. Coba kirim satu pengukuran dengan contoh di bawah, lalu buka **Table Editor → cuaca_sensor** untuk melihat baris yang sama di cloud.

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

Kode 201 berarti pengukuran tersimpan. Buka **Sensor langsung** dan pilih perangkat. Dashboard membaca ulang data setiap 5 detik dan menampilkan hingga 60 pengukuran terakhir perangkat itu. Ulangi blok mulai dari `$body` dengan suhu berbeda untuk melihat pembaruan. Jika kota, nama sensor, dan waktunya sama, kiriman ulang mendapat 200. Jika nilainya berbeda untuk pengukuran yang sama, penerima mengembalikan 409.

Untuk ESP32 atau pengirim lain di Wi-Fi yang sama, jalankan `sensor.py --host 0.0.0.0` dengan Python dari venv. Gunakan alamat IPv4 laptop sebagai pengganti `127.0.0.1`. Perangkat mengirim HTTP POST ke `/pengukuran` dengan header dan kolom JSON yang sama. Isi `waktu` dengan waktu pengukuran beserta zona waktunya, misalnya `2026-11-18T08:30:00+07:00`. Gunakan jaringan lokal tepercaya untuk HTTP ini.

## Cara model membuat prediksi

Aplikasi menghitung suhu rata-rata dari 24 pengukuran per hari dalam arsip 2025, lalu melatih model musiman untuk setiap kota. Saat sensor mencatat suhu pada sedikitnya 18 jam berbeda kemarin (WIB), model menghitung selisih suhu kemarin dari pola musimannya. Pengaruh selisih itu berkurang untuk tanggal yang lebih jauh sesuai hubungan suhu antarhari dalam arsip. Setiap perangkat mendapat bobot yang sama dalam satu jam, lalu tiap jam mendapat bobot yang sama dalam rata-rata harian. Tab memeriksa ulang data setiap menit selama dashboard terbuka.

Untuk mengukur galat, model evaluasi hanya belajar dari Januari–September 2025. Sepanjang Oktober–Desember, pengujian membuat prediksi tujuh hari berulang kali dengan informasi yang tersedia pada tiap tanggal, lalu mencocokkannya dengan suhu sebenarnya dalam arsip. Model yang dipakai dashboard dilatih ulang dengan seluruh tahun 2025 secara otomatis. Saat sensor belum cukup, angka di dashboard hanya mencerminkan pola musiman dari satu tahun arsip. Model ini belum memasukkan prakiraan angin, awan, atau hujan mendatang.

Arsip berisi data per jam sepanjang 2025. Cuaca berasal dari ECMWF ERA5 dan estimasi PM2.5 dari Copernicus Atmosphere Monitoring Service melalui Open-Meteo. Setiap kota diwakili satu titik model. [Arsip cuaca](https://open-meteo.com/en/docs/historical-weather-api) · [Data kualitas udara](https://open-meteo.com/en/docs/air-quality-api) · [Lisensi CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Pengujian

```powershell
.\.venv\Scripts\python uji.py
.\.venv\Scripts\python -m unittest uji_sensor
```

Untuk memperbarui arsip, cadangkan folder `data`, jalankan `ambil_data.py` lalu `analisis.py` dengan Python dari venv. Keduanya menulis ulang data historis.
