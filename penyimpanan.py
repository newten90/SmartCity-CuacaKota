"""Penyimpanan bersama untuk penerima HTTP dan dashboard."""
from contextlib import contextmanager, closing
from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
import sqlite3
import tomllib

import psycopg

ROOT = Path(__file__).resolve().parent
WIB = timezone(timedelta(hours=7))
DB_ERRORS = (sqlite3.Error, psycopg.Error, ValueError, OSError)


def cloud_url():
    if "SUPABASE_DB_URL" in os.environ:
        return os.environ["SUPABASE_DB_URL"]
    path = ROOT / ".streamlit/secrets.toml"
    if path.is_file():
        with path.open("rb") as file:
            return tomllib.load(file).get("SUPABASE_DB_URL", "")
    return ""


@contextmanager
def session():
    url = cloud_url()
    if url:
        with psycopg.connect(url, sslmode="require", connect_timeout=5) as db:
            yield Store(db, True)
    else:
        path = os.getenv("SENSOR_DB") or ROOT / "data/sensor.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS readings (
                kota TEXT, sensor TEXT, waktu TEXT, suhu REAL, kelembapan REAL,
                PRIMARY KEY (kota, sensor, waktu))""")
            yield Store(db, False)


class Store:
    def __init__(self, db, cloud):
        self.db = db
        self.cloud = cloud
        self.table = "public.cuaca_sensor" if cloud else "readings"

    def execute(self, sql, params=()):
        query = sql.format(table=self.table)
        return self.db.execute(query.replace("?", "%s") if self.cloud else query, params)

    def save(self, row):
        result = self.execute("""INSERT INTO {table} (kota,sensor,waktu,suhu,kelembapan)
            VALUES (?,?,?,?,?) ON CONFLICT (kota,sensor,waktu) DO NOTHING""", row)
        if result.rowcount:
            return 201
        saved = self.execute("SELECT suhu,kelembapan FROM {table} WHERE kota=? AND sensor=? AND waktu=?", row[:3]).fetchone()
        return 200 if saved == row[3:] else 409

    def devices(self):
        return self.execute("SELECT DISTINCT kota,sensor FROM {table} ORDER BY kota,sensor").fetchall()

    def history(self, city, sensor):
        rows = self.execute("""SELECT waktu,suhu,kelembapan FROM {table} WHERE kota=? AND sensor=?
            ORDER BY waktu DESC LIMIT 60""", (city, sensor)).fetchall()
        return [(stamp.astimezone(WIB).isoformat() if isinstance(stamp, datetime) else stamp, temp, rh)
                for stamp, temp, rh in rows]

    def daily_temperature(self, city, day):
        start = datetime.combine(day, time(), WIB)
        bounds = [stamp.isoformat(timespec="microseconds") for stamp in (start, start + timedelta(days=1))]
        hour = "extract(hour from waktu at time zone 'Asia/Jakarta')" if self.cloud else "substr(waktu,12,2)"
        # Bobot sama per perangkat dalam satu jam, lalu bobot sama per jam.
        return self.execute("""
            SELECT avg(temp), count(*) FROM (
                SELECT jam, avg(device_temp) AS temp FROM (
                    SELECT """ + hour + """ AS jam, sensor, avg(suhu) AS device_temp
                    FROM {table} WHERE kota=? AND waktu>=? AND waktu<?
                    GROUP BY 1, sensor
                ) per_sensor GROUP BY jam
            ) per_jam""", (city, *bounds)).fetchone()


def initialize_cloud():
    if not cloud_url():
        raise ValueError("SUPABASE_DB_URL belum diisi.")
    with session() as store:
        store.db.execute((ROOT / "supabase.sql").read_text(encoding="utf-8"))
        store.devices()


if __name__ == "__main__":
    try:
        initialize_cloud()
    except DB_ERRORS:
        raise SystemExit("Setup gagal. Periksa SUPABASE_DB_URL, password, koneksi, dan izin membuat tabel.")
    print("Supabase terhubung. Tabel public.cuaca_sensor siap menerima data.")
