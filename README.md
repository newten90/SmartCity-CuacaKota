# Dashboard Cuaca Kota • Minggu 2
Bandung, Jakarta, dan Surabaya | 1 Januari–31 Desember 2025 | WIB

## Menjalankan di Windows
1. Ekstrak ZIP. Buka folder yang berisi app.py di File Explorer. Ketik cmd di bilah alamat lalu tekan Enter.
2. Gunakan Python 3.12. Jalankan perintah berikut satu per satu. Koneksi internet diperlukan untuk instalasi pertama.

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

3. Buka alamat Local URL yang muncul di terminal (biasanya http://localhost:8501). Biarkan terminal terbuka selama demo. Tekan Ctrl+C untuk berhenti.
4. macOS/Linux dapat memakai python3.12 -m venv .venv dan mengganti .venv\Scripts\python dengan .venv/bin/python pada perintah berikutnya.

## Demo tiga menit
Buka Analisis dengan pilihan awal Bandung sepanjang 2025. Cocokkan suhu 24,10 °C dan total hujan 4.270,0 mm. Arahkan kursor ke batang Januari dan Juli. Ganti ke Surabaya dan perhatikan perpindahan puncak hujan ke Mei. Pilih 10–16 Februari dan periksa tanda bulan parsial. Buka Hubungan antarvariabel. Hanya bulan kalender utuh yang masuk korelasi bulanan. Unduh CSV dan cek bahwa baris hanya berisi kota dan tanggal yang dipilih. Buka Simulasi sensor, tekan Data berikutnya dua kali dan periksa waktu WIB bergeser satu jam. Tekan Ulangi dari awal untuk mereset.

## Struktur dan reproduksi
- ambil_data.py meminta dua sumber per kota. Enam JSON menyimpan URL, waktu pengambilan UTC, koordinat yang dikembalikan model, satuan, dan payload asli. Jika API gagal, program memakai arsip lokal yang tersedia.
- data/cuaca_udara.csv adalah masukan dashboard. Kolom waktu dan kota membentuk kunci. temperature_2m (°C), relative_humidity_2m (%), rain (mm/jam sebagai jumlah per interval satu jam), dan pm2_5 (µg/m³) adalah variabel analisis. tanggal, bulan, jam diturunkan dari waktu lokal.
- analisis.py menerapkan agregasi. data/harian.csv dan data/bulanan.csv adalah ringkasan periode penuh. app.py membaca CSV lalu menghitung ulang untuk tanggal pilihan pengguna.
- uji.py menjalankan aplikasi melalui Streamlit AppTest dan membandingkan setiap indikator dengan perhitungan Pandas terpisah. Hasilnya tersimpan di bukti/uji_indikator.csv.
- Untuk mengulang uji, jalankan .venv\Scripts\python uji.py. Untuk mengambil ulang data, cadangkan folder data sebelum menjalankan .venv\Scripts\python ambil_data.py. API dapat memperbarui arsip. Jalankan .venv\Scripts\python analisis.py untuk memperbarui dua ringkasan, lalu jalankan kembali uji.

## Publikasi cloud dari akun kelompok
1. Pastikan tim sudah mengonfirmasi penggunaan Streamlit sesuai proposal. Siapkan repositori GitHub milik kelompok. Unggah app.py, analisis.py, requirements.txt, README.md, dan data/cuaca_udara.csv dengan susunan folder tetap. Dokumen identitas kelompok dan hasil pengujian cukup disimpan di berkas tugas.
2. Masuk ke https://share.streamlit.io dengan akun kelompok yang berhak mengakses repositori. Pilih Create app, lalu pilih opsi untuk memakai aplikasi yang sudah ada. Isi nama repositori, cabang, dan lokasi app.py. Jika aplikasi berada di subfolder, gunakan path lengkap relatif terhadap akar repositori.
3. Di pengaturan lanjutan pilih Python 3.12. Klik Deploy. Sesudah dashboard tampil, salin URL berakhiran streamlit.app. Pastikan visibilitas aplikasi mengizinkan pengunjung membuka tautan.
4. Buka tautan dari jendela privat tanpa login. Pilih Jakarta, ubah tanggal, unduh CSV dan coba simulasi. Catat URL, waktu uji dan hasilnya dalam laporan. Ambil tangkapan layar yang menampilkan URL publik. Jika gagal, periksa log deployment, jalur berkas utama, versi Python, dan keberadaan CSV.
Panduan resmi: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Asal data dan penggunaan
Cuaca: Open-Meteo Historical Weather API, ECMWF ERA5 (https://open-meteo.com/en/docs/historical-weather-api). Estimasi PM2.5: Copernicus Atmosphere Monitoring Service, CAMS global melalui Open-Meteo (https://open-meteo.com/en/docs/air-quality-api). Lisensi data via Open-Meteo: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Kelompok menyelaraskan waktu, memeriksa nilai dan membuat agregat. API digunakan untuk pendidikan nonkomersial. Satu titik grid per sumber per kota. Resolusi asli CAMS global tiga jam, sedangkan keluaran API tersedia tiap jam. Angka PM2.5 adalah estimasi historis. Simulasi menggunakan arsip, tanpa sensor fisik atau pelacakan warga.
