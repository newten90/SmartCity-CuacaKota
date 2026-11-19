"""Uji endpoint, penerima sensor POST /pengukuran, dan logika sinkron riwayat.
Semua berjalan tanpa internet dan tanpa database asli:  python -m unittest uji_api"""
import os
os.environ["SUPABASE_DB_URL"] = ""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd
import psycopg
from fastapi.testclient import TestClient

import layanan
import main
import sinkron_riwayat as sinkron
from penyimpanan import WIB

client = TestClient(main.app)


def laporan_palsu(today, jam_sekarang=9):
    """Respons Open-Meteo tiruan untuk hari today (bentuk sama dengan prakiraan.outlook())."""
    days = [today + timedelta(days=n) for n in range(0, 8)]
    hours = pd.date_range(pd.Timestamp(today), periods=8 * 24, freq="h")
    return {
        "current": {"time": f"{today.isoformat()}T{jam_sekarang:02d}:30", "temperature_2m": 26.2,
                    "relative_humidity_2m": 71, "apparent_temperature": 30.2, "weather_code": 3,
                    "wind_speed_10m": 4.9},
        "hourly": {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in hours],
                   "temperature_2m": [20 + t.hour / 2 for t in hours],
                   "precipitation_probability": [65 if (t.hour == 13 and t.date() == today) else 20 for t in hours],
                   "weather_code": [61 for _ in hours]},
        "daily": {"time": [d.isoformat() for d in days],
                  "temperature_2m_min": [20.5] * 8, "temperature_2m_max": [27.0] * 8,
                  "temperature_2m_mean": [23.0] * 8, "weather_code": [95] * 8,
                  "precipitation_probability_max": [80] * 8, "precipitation_sum": [5.5] * 8,
                  "wind_speed_10m_max": [9.0] * 8,
                  "sunrise": [f"{d.isoformat()}T05:37" for d in days],
                  "sunset": [f"{d.isoformat()}T17:52" for d in days]},
    }


class Dasar(unittest.TestCase):
    def setUp(self):
        layanan.bersihkan_cache()
        self.addCleanup(layanan.bersihkan_cache)


class TestValidasi(Dasar):
    def test_kota_tidak_valid_400(self):
        for path in ["/api/cuaca", "/api/riwayat", "/api/riwayat.csv", "/api/analisis", "/api/analisis.csv",
                     "/api/sensor"]:
            with self.subTest(path=path):
                response = client.get(path, params={"kota": "Medan"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("Bandung", response.json()["pesan"])
        self.assertEqual(client.get("/api/riwayat", params={"kota": ""}).status_code, 400)

    def test_tanggal_tidak_valid_400(self):
        cases = [("2024-12-31", "2025-01-02"), ("2025-01-01", "2026-01-01"), ("2025-03-01", "2025-02-01"),
                 ("2025-02-30", "2025-03-01"), ("1/1/2025", "2025-02-01"), ("2025-01-01", None), (None, "2025-01-01")]
        for dari, sampai in cases:
            with self.subTest(dari=dari, sampai=sampai):
                params = {"kota": "Bandung", **{k: v for k, v in (("dari", dari), ("sampai", sampai)) if v}}
                for path in ["/api/analisis", "/api/analisis.csv"]:
                    response = client.get(path, params=params)
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(response.json()["pesan"])
        self.assertEqual(client.get("/api/analisis", params={"kota": "Bandung", "dari": "2025-01-01"}).json()["pesan"],
                         "Pilih tanggal akhir untuk menghitung ringkasan.")

    def test_alamat_tidak_ada_json(self):
        response = client.get("/api/tidak-ada")
        self.assertEqual(response.status_code, 404)
        self.assertIn("pesan", response.json())


class TestAnalisis(Dasar):
    def test_bentuk_respons(self):
        response = client.get("/api/analisis", params={"kota": "Surabaya", "dari": "2025-01-01", "sampai": "2025-03-31"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["jam"], 90 * 24)
        self.assertEqual(sorted(body["indikator"]), sorted(["temperature_2m", "relative_humidity_2m", "rain", "pm2_5"]))
        self.assertEqual(len(body["harian"]), 90)
        self.assertEqual([m["bulan"] for m in body["bulanan"]], ["2025-01", "2025-02", "2025-03"])
        self.assertTrue(all(m["bulan_utuh"] for m in body["bulanan"]))
        self.assertEqual([row["kota"] for row in body["tabel_kota"]], ["Bandung", "Jakarta", "Surabaya"])
        self.assertIsNone(body["bulan_parsial"])
        self.assertTrue(body["temuan"])

    def test_bulan_parsial_dan_csv(self):
        params = {"kota": "Bandung", "dari": "2025-02-10", "sampai": "2025-02-16"}
        body = client.get("/api/analisis", params=params).json()
        self.assertFalse(body["bulanan"][0]["bulan_utuh"])
        self.assertIn("2025-02", body["bulan_parsial"])
        self.assertIsNone(body["kartu"]["terbasah"])
        response = client.get("/api/analisis.csv", params=params)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bandung_2025-02-10_2025-02-16.csv", response.headers["content-disposition"])
        self.assertEqual(len(response.text.strip().splitlines()), 1 + 7 * 24)

    def test_korelasi_belum_tersedia(self):
        body = client.get("/api/analisis", params={"kota": "Bandung", "dari": "2025-08-01", "sampai": "2025-08-01"}).json()
        self.assertEqual(body["korelasi"]["hujan_pm25"]["teks"], "Korelasi belum tersedia · 0 pasangan")
        self.assertIsNone(body["korelasi"]["hujan_pm25"]["r"])


class TestRiwayat(Dasar):
    def test_fallback_csv_saat_database_tidak_tersedia(self):
        @contextmanager
        def gagal():
            raise psycopg.OperationalError("tidak terjangkau")
            yield

        with patch.dict(os.environ, SUPABASE_DB_URL="postgresql://pengguna:rahasia@tidak-ada.invalid/db"), \
                patch("layanan.session", gagal):
            body = client.get("/api/riwayat", params={"kota": "Jakarta"}).json()
            response = client.get("/api/riwayat.csv", params={"kota": "Jakarta"})
        self.assertEqual(body["sumber_data"], "salinan impor di repositori")
        self.assertIn("Supabase tidak terjangkau", body["catatan"])
        self.assertNotIn("rahasia", str(body))
        self.assertGreater(body["jumlah"], 1000)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text.startswith("kota,waktu,temperature_2m"))
        self.assertIn("Jakarta_riwayat_online.csv", response.headers["content-disposition"])

    def test_tanpa_uri_memakai_csv_dan_tidak_menyentuh_database(self):
        with patch("layanan.session", side_effect=AssertionError("tidak boleh dipanggil")):
            body = client.get("/api/riwayat", params={"kota": "Bandung", "terbaru": 5}).json()
        self.assertEqual(body["sumber_data"], "salinan impor di repositori")
        self.assertIn("SUPABASE_DB_URL kosong", body["catatan"])
        self.assertEqual(len(body["baris"]), 5)
        self.assertEqual(body["baris"][-1]["waktu"], body["akhir"])

    def test_supabase_dan_penanda_data_usang(self):
        rows = [("Bandung", datetime(2026, 11, 19, 1) + timedelta(hours=h), 22.0 + h, 80, 0.0, 3.0, 3, None, "Open-Meteo ERA5")
                for h in range(3)]

        class Db:
            def execute(self, sql, params=()):
                return self

            def fetchall(self):
                return rows

        class Store:
            cloud, db = True, Db()

        @contextmanager
        def palsu():
            yield Store()

        with patch.dict(os.environ, SUPABASE_DB_URL="postgresql://x"), patch("layanan.session", palsu):
            terbaru = layanan.riwayat("Bandung", now=datetime(2026, 11, 19, 4, 30, tzinfo=WIB))
            layanan.bersihkan_cache()
            usang = layanan.riwayat("Bandung", now=datetime(2026, 11, 19, 12, 0, tzinfo=WIB))
        self.assertEqual(terbaru["sumber_data"], "Supabase")
        self.assertIsNone(terbaru["catatan"])
        self.assertEqual(terbaru["jumlah"], 3)
        self.assertEqual(terbaru["akhir"], "2026-11-19T03:00")
        self.assertFalse(terbaru["usang"])
        self.assertIsNone(terbaru["baris"][0]["pm2_5"])
        self.assertTrue(usang["usang"])
        self.assertEqual(usang["selisih_jam"], 9.0)


class TestCuaca(Dasar):
    def test_503_saat_outlook_gagal(self):
        for error in [OSError("tak ada internet"), ValueError("bukan JSON"), TimeoutError()]:
            with self.subTest(error=error), patch("layanan.outlook", side_effect=error):
                layanan.bersihkan_cache()
                response = client.get("/api/cuaca", params={"kota": "Bandung"})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["pesan"], layanan.PESAN_PRAKIRAAN)
                self.assertEqual(response.headers["cache-control"], "no-store")

    def test_respons_tanggal_berbeda_dianggap_gagal(self):
        kemarin = datetime.now(WIB).date() - timedelta(days=1)
        with patch("layanan.outlook", return_value=laporan_palsu(kemarin)):
            self.assertEqual(client.get("/api/cuaca", params={"kota": "Bandung"}).status_code, 503)

    def test_respons_normal(self):
        today = datetime.now(WIB).date()
        with patch("layanan.outlook", return_value=laporan_palsu(today)) as outlook:
            response = client.get("/api/cuaca", params={"kota": "Jakarta"})
            client.get("/api/cuaca", params={"kota": "Jakarta"})
        self.assertEqual(outlook.call_count, 1, "cache dalam proses dipakai")
        self.assertEqual(response.status_code, 200)
        self.assertIn("s-maxage=900", response.headers["cache-control"])
        self.assertIn("stale-while-revalidate", response.headers["cache-control"])
        body = response.json()
        self.assertEqual(body["kota"], "Jakarta")
        self.assertEqual(body["sekarang"]["kondisi"], {"ikon": "berawan", "label": "Berawan"})
        self.assertEqual((body["sekarang"]["terbit"], body["sekarang"]["terbenam"]), ("05:37", "17:52"))
        self.assertEqual(body["per_jam"][0]["jam"], "Kini")
        self.assertEqual(len(body["per_jam"]), 1 + 24)
        self.assertEqual([d["tanggal"] for d in body["tujuh_hari"]],
                         [(today + timedelta(days=n)).isoformat() for n in range(1, 8)])
        self.assertEqual(body["tujuh_hari"][0]["kondisi"]["ikon"], "petir")
        self.assertEqual(body["tips_hujan"], {"jam": "13:00", "peluang": 65})
        self.assertIn("nilai", body["pm25"])

    def test_tips_hujan_hanya_bila_peluang_50_ke_atas(self):
        today = datetime.now(WIB).date()
        report = laporan_palsu(today)
        report["hourly"]["precipitation_probability"] = [49] * len(report["hourly"]["time"])
        with patch("layanan.outlook", return_value=report):
            self.assertIsNone(client.get("/api/cuaca", params={"kota": "Bandung"}).json()["tips_hujan"])

    def test_nan_menjadi_null(self):
        today = datetime.now(WIB).date()
        report = laporan_palsu(today)
        report["daily"]["precipitation_sum"][2] = None
        report["daily"]["sunrise"][0] = None
        with patch("layanan.outlook", return_value=report):
            body = client.get("/api/cuaca", params={"kota": "Bandung"}).json()
        self.assertIsNone(body["tujuh_hari"][1]["presipitasi"])
        self.assertIsNone(body["sekarang"]["terbit"])


class TestSensor(Dasar):
    def setUp(self):
        super().setUp()
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = patch.dict(os.environ, SUPABASE_DB_URL="", SENSOR_DB=str(Path(folder.name) / "uji.sqlite3"),
                             SENSOR_TOKEN="test")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.body = dict(sensor="uji", kota="Bandung", waktu=datetime.now(WIB).isoformat(), suhu=26, kelembapan=78)

    def kirim(self, data, token="test", raw=None):
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        content = raw if raw is not None else __import__("json").dumps(data)
        return client.post("/pengukuran", content=content, headers=headers).status_code

    def test_kode_balasan_sama_dengan_sensor_py(self):
        now = datetime.now(WIB)
        self.assertEqual(self.kirim(self.body, "salah"), 401)
        self.assertEqual(self.kirim(self.body, None), 401)
        self.assertEqual(self.kirim(dict(self.body, kelembapan=101)), 400)
        self.assertEqual(self.kirim(self.body), 201)
        self.assertEqual(self.kirim(self.body), 200)
        self.assertEqual(self.kirim(dict(self.body, suhu=27)), 409)
        earlier = now.replace(minute=0, second=0, microsecond=0)
        self.assertEqual(self.kirim(dict(self.body, waktu=earlier.isoformat(), suhu=20)), 201)
        from penyimpanan import session
        with session() as store:
            history = store.history("Bandung", "uji")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][1], 26)

    def test_validasi_badan(self):
        self.assertEqual(self.kirim(None, raw="bukan json"), 400)
        self.assertEqual(self.kirim(None, raw=""), 400)
        self.assertEqual(self.kirim(None, raw="[1, 2]"), 400)
        self.assertEqual(self.kirim(None, raw="[" * 100000), 400)
        self.assertEqual(self.kirim(dict(self.body, kota="Medan")), 400)
        self.assertEqual(self.kirim(dict(self.body, sensor="  ")), 400)
        self.assertEqual(self.kirim(dict(self.body, waktu="2026-01-01T00:00:00")), 400)
        self.assertEqual(self.kirim(dict(self.body, waktu=(datetime.now(WIB) + timedelta(hours=1)).isoformat())), 400)
        self.assertEqual(self.kirim(dict(self.body, sensor="x" * 5000)), 400)
        self.assertEqual(self.kirim(dict(self.body, suhu=True)), 400)

    def test_tanpa_token_di_server_503(self):
        with patch.dict(os.environ, SENSOR_TOKEN=""):
            self.assertEqual(self.kirim(self.body, ""), 503)
            self.assertEqual(self.kirim(self.body, "test"), 503)

    def test_database_gagal_503(self):
        @contextmanager
        def gagal():
            raise psycopg.OperationalError("mati")
            yield

        with patch("layanan.session", gagal):
            self.assertEqual(self.kirim(self.body), 503)
            response = client.get("/api/sensor", params={"kota": "Bandung"})
            self.assertEqual(response.status_code, 503)

    def test_vercel_tanpa_supabase_pesan_jelas(self):
        with patch.dict(os.environ, VERCEL="1", SUPABASE_DB_URL=""):
            response = client.post("/pengukuran", content="{}", headers={"Authorization": "Bearer test"})
            self.assertEqual(response.status_code, 400)  # badan dicek lebih dulu
            self.assertEqual(self.kirim(self.body), 503)
            response = client.get("/api/sensor", params={"kota": "Bandung"})
            self.assertEqual(response.status_code, 503)
            self.assertIn("SUPABASE_DB_URL", response.json()["pesan"])
            self.assertIn("Vercel", response.json()["pesan"])

    def test_api_sensor(self):
        response = client.get("/api/sensor", params={"kota": "Bandung"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["perangkat"], [])
        self.assertIsNone(response.json()["terbaru"])

        now = datetime.now(WIB)
        self.assertEqual(self.kirim(dict(self.body, waktu=now.isoformat(), suhu=26.4, kelembapan=78)), 201)
        self.assertEqual(self.kirim(dict(self.body, waktu=(now - timedelta(minutes=5)).isoformat(), suhu=26.0)), 201)
        self.assertEqual(self.kirim(dict(self.body, sensor="lama", waktu=(now - timedelta(hours=2)).isoformat())), 201)
        body = client.get("/api/sensor", params={"kota": "Bandung"}).json()
        self.assertEqual([d["sensor"] for d in body["perangkat"]], ["uji", "lama"])
        self.assertTrue(body["perangkat"][0]["aktif"])
        self.assertFalse(body["perangkat"][1]["aktif"])
        self.assertEqual(body["perangkat"][0]["kiriman_1_jam"], 2)
        self.assertEqual(body["sumber"], "SQLite lokal")
        self.assertEqual(body["terbaru"]["sensor"], "uji")
        self.assertEqual(body["terbaru"]["suhu"], 26.4)
        self.assertEqual([row["suhu"] for row in body["pengukuran"]["uji"]], [26.4, 26.0])
        self.assertIsNone(body["terbaru"]["model_suhu"], "belum ada riwayat model untuk jam ini")
        self.assertEqual(client.get("/api/sensor", params={"kota": "Jakarta"}).json()["perangkat"], [])

    def test_suhu_model_jam_yang_sama(self):
        stamp = datetime(2026, 11, 18, 22, 40, tzinfo=WIB)
        self.assertEqual(self.kirim(dict(self.body, waktu=stamp.isoformat(), suhu=30)), 201)
        local = pd.DataFrame({"waktu": [pd.Timestamp("2026-11-18 22:00")], "temperature_2m": [25.0]})
        with patch("layanan._riwayat_kota", return_value=(local, "x")):
            body = layanan.sensor("Bandung", now=stamp)
        self.assertEqual(body["terbaru"]["model_suhu"], 25.0)
        self.assertEqual(body["terbaru"]["selisih"], 5.0)


class TestHalaman(Dasar):
    def test_halaman_dan_berkas_statis(self):
        for path in ["/", "/analisis", "/riwayat", "/sensor", "/kota"]:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
        self.assertEqual(client.get("/static/css/app.css").status_code, 200)

    def test_daftar_kota(self):
        body = client.get("/api/kota").json()
        self.assertEqual([k["nama"] for k in body], ["Bandung", "Jakarta", "Surabaya"])


# ---------- sinkron riwayat ----------
def hourly_palsu(calls, hilang=()):
    def hourly(url, city, start, end, fields, **params):
        calls.append((url, start, end, params))
        index = pd.date_range(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23), freq="h")
        frame = pd.DataFrame({field: 1.0 for field in fields}, index=index)
        if "temperature_2m" in fields:
            frame.loc[frame.index.isin(hilang), "temperature_2m"] = float("nan")
        return frame
    return hourly


class TestSinkron(unittest.TestCase):
    def test_potong_rentang_era5_dan_model_operasional(self):
        today = date(2026, 11, 19)
        chunks = sinkron.potong(date(2026, 10, 1), today)
        # ERA5 sampai 7 hari lalu, model operasional untuk 6 hari terakhir termasuk hari ini.
        self.assertEqual(chunks[0], (True, date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(chunks[-1], (False, date(2026, 11, 13), today))
        self.assertEqual([c[0] for c in chunks], [True, True, False])
        for (_, _, end), (_, nxt, _) in zip(chunks, chunks[1:]):
            self.assertEqual(nxt, end + timedelta(days=1), "tidak ada celah atau tumpang tindih")
        self.assertTrue(all((end - start).days <= 30 for _, start, end in chunks))
        # Inkremental 10 hari: 4 hari ERA5 lalu 7 hari model operasional.
        self.assertEqual(sinkron.potong(today - timedelta(days=10), today),
                         [(True, date(2026, 11, 9), date(2026, 11, 12)), (False, date(2026, 11, 13), today)])
        self.assertEqual(sinkron.potong(today, today), [(False, today, today)])
        self.assertEqual(sinkron.potong(today + timedelta(days=1), today), [])

    def test_awal_inkremental(self):
        today = date(2026, 11, 19)
        self.assertEqual(sinkron.mulai(None, today), sinkron.START)
        self.assertEqual(sinkron.mulai(datetime(2026, 11, 19, 3), today), date(2026, 11, 9))
        self.assertEqual(sinkron.mulai(datetime(2026, 11, 1, 3), today), date(2026, 11, 1), "menutup jeda sinkron yang lama")
        self.assertEqual(sinkron.mulai(datetime(2026, 9, 1), today), sinkron.START)

    def test_city_history_label_sumber_dan_jam_kosong(self):
        now = datetime(2026, 11, 19, 5, 40, tzinfo=WIB)
        start = date(2026, 11, 9)
        hilang = [pd.Timestamp("2026-11-10 03:00"), pd.Timestamp("2026-11-18 12:00")]
        calls = []
        with patch.object(sinkron, "hourly", hourly_palsu(calls, hilang)):
            frame, missing = sinkron.city_history("Bandung", now, start)
        self.assertEqual(missing, hilang, "jam kosong dicatat, bukan menggagalkan sinkron")
        self.assertEqual(list(frame.columns), sinkron.COLS)
        self.assertEqual(frame.waktu.min(), pd.Timestamp("2026-11-09 00:00"))
        self.assertEqual(frame.waktu.max(), pd.Timestamp("2026-11-19 05:00"), "dipotong di jam berjalan")
        self.assertEqual(len(frame), 10 * 24 + 6 - 2)
        self.assertFalse(frame.waktu.duplicated().any())
        self.assertNotIn(hilang[0], set(frame.waktu))
        sumber = frame.set_index("waktu").sumber
        self.assertEqual(sumber["2026-11-12 23:00"], "Open-Meteo ERA5")
        self.assertEqual(sumber["2026-11-13 00:00"], "Open-Meteo Best Match")
        self.assertEqual(frame.weather_code.dtype.kind, "i")
        weather = [c for c in calls if c[0] != sinkron.AIR]
        self.assertEqual([(c[0], str(c[1]), str(c[2]), c[3]) for c in weather], [
            (sinkron.ARCHIVE, "2026-11-09", "2026-11-12", {"models": "era5"}),
            (sinkron.FORECAST, "2026-11-13", "2026-11-19", {})])
        self.assertEqual(len([c for c in calls if c[0] == sinkron.AIR]), 2)

    def test_city_history_semua_kosong_tidak_error(self):
        now = datetime(2026, 11, 19, 5, 40, tzinfo=WIB)
        everything = list(pd.date_range("2026-11-19", "2026-11-19 05:00", freq="h"))
        with patch.object(sinkron, "hourly", hourly_palsu([], everything)):
            frame, missing = sinkron.city_history("Jakarta", now, date(2026, 11, 19))
        self.assertTrue(frame.empty)
        self.assertEqual(len(missing), 6)

    def test_sync_menyimpan_yang_lengkap_dan_meringkas(self):
        now = datetime(2026, 11, 19, 5, 40, tzinfo=WIB)
        saved = []

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def executemany(self, sql, rows):
                saved.extend(rows)

        class Db:
            def execute(self, sql, params=()):
                self.last = sql
                return self

            def fetchall(self):
                return [("Bandung", datetime(2026, 11, 18, 23))]

            def cursor(self):
                return Cursor()

        class Store:
            cloud, db = True, Db()

        @contextmanager
        def palsu():
            yield Store()

        original = sinkron.city_history

        def city_history(city, now_, start):
            if city == "Surabaya":
                raise OSError("Open-Meteo menolak")
            return original(city, now_, start)

        hilang = [pd.Timestamp("2026-11-18 12:00")]
        with patch.object(sinkron, "hourly", hourly_palsu([], hilang)), patch.object(sinkron, "session", palsu), \
                patch.object(sinkron, "initialize_cloud"), patch.object(sinkron, "city_history", city_history):
            summary = sinkron.sync(now=now)
        self.assertEqual(summary["Bandung"]["awal"], "2026-11-09")
        self.assertEqual(summary["Jakarta"]["awal"], "2026-10-01", "kota tanpa data mulai dari 1 Oktober")
        self.assertEqual(summary["Jakarta"]["kosong"], ["2026-11-18 12:00"])
        self.assertIn("OSError", summary["Surabaya"]["galat"])
        self.assertEqual(summary["Surabaya"]["disimpan"], 0)
        self.assertEqual(len(saved), summary["Bandung"]["disimpan"] + summary["Jakarta"]["disimpan"])
        self.assertTrue(all(row[1].tzinfo is not None for row in saved), "waktu disimpan beserta zona WIB")
        self.assertTrue(all(row[2] is not None for row in saved))

    def test_csv_hanya_ditulis_dengan_opsi(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "riwayat.csv"
            with patch.object(sinkron, "SNAPSHOT", target):
                sinkron._write_csv(pd.DataFrame({"kota": ["Bandung"], "waktu": [pd.Timestamp("2026-11-19")]}))
            self.assertTrue(target.read_text(encoding="utf-8").startswith("kota,waktu"))
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["riwayat.csv"])


class TestLingkungan(unittest.TestCase):
    def test_muat_env_tidak_menimpa_dan_membuang_kutip(self):
        import lingkungan
        with TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text('# komentar\nSUPABASE_DB_URL="postgresql://a"\nSENSOR_TOKEN=abc\nBARU_UJI=ya\nrusak\n', encoding="utf-8")
            with patch.dict(os.environ, {"SENSOR_TOKEN": "sudah-ada", "SUPABASE_DB_URL": ""}):
                os.environ.pop("BARU_UJI", None)
                lingkungan.muat_env(path)
                self.assertEqual(os.environ["SUPABASE_DB_URL"], "", "nilai yang sudah ada tidak ditimpa")
                self.assertEqual(os.environ["SENSOR_TOKEN"], "sudah-ada")
                self.assertEqual(os.environ["BARU_UJI"], "ya")


if __name__ == "__main__":
    unittest.main()
