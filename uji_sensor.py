import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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
        now = datetime.now(WIB)
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
        from penyimpanan import session
        with session() as store:
            history = store.history("Bandung", "uji")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][1], 26)
