# Cuaca Kota

Cuaca Kota menampilkan cuaca dan kualitas udara Bandung, Jakarta, dan Surabaya. Di tab **Analisis 2025**, pilih kota dan rentang tanggal untuk melihat suhu, kelembapan, total hujan, dan PM2.5. Grafik dan unduhan CSV mengikuti tanggal yang dipilih. Untuk membandingkan hujan dan PM2.5 antarbulan, aplikasi hanya memakai bulan dengan data lengkap.

Tab **Sensor langsung** menampilkan suhu dan kelembapan yang dikirim perangkat, waktu pengukuran dalam WIB, serta perkiraan suhu satu jam setelah pengukuran terakhir. Kalau belum punya perangkat, coba kirim contoh dari PowerShell di bawah. Ada juga tab **Simulasi sensor** untuk memutar ulang 24 jam pertama arsip Bandung, satu jam per klik.

Di tab **Prediksi suhu**, pilih kota lalu masukkan suhu, kelembapan, dan jam pengukuran dalam WIB. Perkiraan suhu satu jam berikutnya langsung berubah saat isian diganti. Tab ini bisa dicoba sebelum sensor mengirim data.

## Menjalankan dashboard

Dari folder proyek, jalankan di PowerShell dengan Python 3.12 atau 3.13.

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Buka alamat lokal yang muncul di terminal. Analisis dan simulasi langsung bisa dipakai karena arsip 2025 sudah ada di folder `data`.

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

## Perlu Supabase?

Untuk demo satu jaringan, cukup jalankan penerima dan Streamlit di laptop yang sama. Penerima menyimpan kiriman ke `data/sensor.sqlite3` sehingga riwayat masih ada setelah aplikasi ditutup. Lokasinya bisa diatur lewat `SENSOR_DB` di kedua proses.

Kalau dashboard dipasang di cloud sementara penerima tetap di laptop, dashboard cloud perlu jalur untuk membaca data itu. Pilihannya antara lain menjalankan kedua proses di satu server dengan disk persisten dan endpoint HTTPS, atau menghubungkan keduanya ke database bersama seperti Supabase. Versi ini memakai SQLite lokal. Push ke GitHub hanya mengirim kode dan arsip, sedangkan pengukuran baru tetap tersimpan di mesin penerima.

## Tentang prediksi dan arsip

Model regresi linear dilatih per kota dari pasangan data yang berjarak tepat satu jam. Masukannya suhu, kelembapan, dan jam lokal. Data Januari–September 2025 dipakai untuk latihan, lalu Oktober–Desember untuk pengujian. Di samping prediksi, dashboard menampilkan rata-rata selisih absolut dalam °C dan pembanding sederhana yang menganggap suhu akan tetap sama. Angka galat tersebut berasal dari arsip cuaca. Akurasi di lokasi pemasangan sensor perlu diukur dengan data perangkat itu sendiri.

Arsip berisi data per jam sepanjang 2025. Cuaca berasal dari ECMWF ERA5 dan estimasi PM2.5 dari Copernicus Atmosphere Monitoring Service melalui Open-Meteo. Setiap kota diwakili satu titik model. [Arsip cuaca](https://open-meteo.com/en/docs/historical-weather-api) · [Data kualitas udara](https://open-meteo.com/en/docs/air-quality-api) · [Lisensi CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Pengujian

```powershell
.\.venv\Scripts\python uji.py
.\.venv\Scripts\python -m unittest uji_sensor
```

Untuk memperbarui arsip, cadangkan folder `data`, jalankan `ambil_data.py` lalu `analisis.py` dengan Python dari venv. Keduanya menulis ulang data historis.
