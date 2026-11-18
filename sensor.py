"""Penerima HTTP untuk pengukuran sensor. Jalankan bersama dashboard."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3

from ambil_data import CITIES

WIB = timezone(timedelta(hours=7))


def connect():
    path = os.getenv("SENSOR_DB") or Path(__file__).parent / "data/sensor.sqlite3"
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS readings (
        kota TEXT, sensor TEXT, waktu TEXT, suhu REAL, kelembapan REAL,
        PRIMARY KEY (kota, sensor, waktu))""")
    return db


def measurement(body):
    if not isinstance(body, dict) or body.get("kota") not in list(CITIES):
        raise ValueError("Pilih Bandung, Jakarta, atau Surabaya.")
    sensor = body.get("sensor")
    if not isinstance(sensor, str) or not 1 <= len(sensor.strip()) <= 64:
        raise ValueError("Isi nama sensor (1–64 karakter).")
    try:
        stamp = datetime.fromisoformat(body["waktu"])
        if stamp.utcoffset() is None:
            raise ValueError
        stamp = stamp.astimezone(WIB)
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError("Gunakan waktu ISO 8601 dengan zona waktu.") from None
    if stamp > datetime.now(WIB) + timedelta(minutes=1):
        raise ValueError("Waktu pengukuran mendahului jam server.")
    for field, low, high in [("suhu", -80, 70), ("kelembapan", 0, 100)]:
        value = body.get(field)
        if type(value) not in (float, int) or not low <= value <= high:
            raise ValueError(f"{field} harus berupa angka antara {low} dan {high}.")
    return body["kota"], sensor.strip(), stamp.isoformat(timespec="microseconds"), body["suhu"], body["kelembapan"]


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/pengukuran":
            return self.send_error(404)
        auth = self.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(auth, self.server.authorization):
            return self.send_error(401)
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size <= 4096:
                raise ValueError("Ukuran JSON harus 1–4096 byte.")
            row = measurement(json.loads(self.rfile.read(size)))
        except (ValueError, RecursionError) as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(exc).encode())
            return
        try:
            with closing(connect()) as db, db:
                inserted = db.execute("INSERT OR IGNORE INTO readings VALUES (?,?,?,?,?)", row).rowcount
                if not inserted:
                    saved = db.execute("SELECT suhu, kelembapan FROM readings WHERE kota=? AND sensor=? AND waktu=?", row[:3]).fetchone()
                    if tuple(saved) != row[3:]:
                        return self.send_error(409)
        except sqlite3.Error:
            return self.send_error(503)
        self.send_response(201 if inserted else 200)
        self.end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    token = os.getenv("SENSOR_TOKEN")
    if not token:
        parser.error("Tetapkan SENSOR_TOKEN sebelum menjalankan penerima.")
    with ThreadingHTTPServer((args.host, args.port), Receiver) as server:
        server.authorization = f"Bearer {token}".encode()
        print(f"Penerima aktif di {args.host}:{args.port}", flush=True)
        server.serve_forever()
