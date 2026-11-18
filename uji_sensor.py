import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from streamlit.testing.v1 import AppTest
from analisis import ROOT, load
from prediksi import forecast, train
from sensor import Receiver, ThreadingHTTPServer, WIB


class TestSensor(unittest.TestCase):
    def test_http_dashboard(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, SUPABASE_DB_URL="", SENSOR_DB=str(Path(folder) / "test.sqlite3")):
            with ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as server:
                server.authorization = b"Bearer test"
                worker = Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    self.check_readings(server.server_port)
                finally:
                    server.shutdown()
                    worker.join()

    def check_readings(self, port):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=35).run()
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs], ["Cuaca & prediksi", "Analisis 2025", "Simulasi sensor"])
        now = datetime.now(WIB)
        tab = app.tabs[0]
        self.assertEqual(len(tab.number_input), 0)
        daily = next(table.value for table in tab.dataframe if "Suhu rata-rata (°C)" in table.value)
        self.assertEqual(len(daily), 7)
        self.assertEqual(daily.iloc[0, 0], (now + timedelta(days=1)).strftime("%d/%m/%Y"))
        body = dict(sensor="uji", kota="Bandung", waktu=now.isoformat(), suhu=26, kelembapan=78)

        def send(data, token="test"):
            request = Request(f"http://127.0.0.1:{port}/pengukuran", data=json.dumps(data).encode(),
                              headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=5) as response:
                    return response.status
            except HTTPError as error:
                error.close()
                return error.code

        self.assertEqual(send(body, "salah"), 401)
        self.assertEqual(send(dict(body, kelembapan=101)), 400)
        self.assertEqual(send(body), 201)
        self.assertEqual(send(body), 200)
        self.assertEqual(send(dict(body, suhu=27)), 409)
        earlier = now.replace(minute=0, second=0, microsecond=0)
        self.assertEqual(send(dict(body, waktu=earlier.isoformat(), suhu=20)), 201)
        app.run()
        self.assertFalse(app.exception)
        from penyimpanan import session
        with session() as store:
            history = store.history("Bandung", "uji")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][1], 26)
        from cuaca_online import SNAPSHOT
        import pandas as pd
        online = pd.read_csv(SNAPSHOT)
        online["tanggal"] = online.waktu.str[:10]
        models = train(pd.concat([load(), online[online.tanggal < now.date().isoformat()]]))
        self.assertEqual(set(models), {"Bandung", "Surabaya", "Jakarta"})
        yesterday = now.date() - timedelta(days=1)
        for hour in range(18):
            stamp = datetime.combine(yesterday, time(hour), WIB)
            self.assertEqual(send(dict(body, sensor="harian", waktu=stamp.isoformat(), suhu=30)), 201)
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("18 jam terukur" in item.value for item in app.tabs[0].caption))
        predicted = forecast(models["Bandung"][0], now.date(), 30)
        daily = next(table.value for table in app.tabs[0].dataframe if "Suhu rata-rata (°C)" in table.value)
        self.assertEqual(list(daily.iloc[:, 1]), predicted.round(1).tolist())
