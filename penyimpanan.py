"""Koneksi PostgreSQL untuk riwayat cuaca."""
from contextlib import contextmanager
from datetime import timedelta, timezone
import os
from pathlib import Path
from lingkungan import muat_env

import psycopg

muat_env()

ROOT = Path(__file__).resolve().parent
WIB = timezone(timedelta(hours=7))
DB_ERRORS = (psycopg.Error, ValueError, OSError)


def cloud_url():
    return os.getenv("SUPABASE_DB_URL", "")


@contextmanager
def session():
    if not cloud_url():
        raise ValueError("SUPABASE_DB_URL belum diisi.")
    with psycopg.connect(cloud_url(), sslmode="require", connect_timeout=5) as db:
        yield db


def initialize_cloud():
    with session() as db:
        db.execute((ROOT / "supabase.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    try:
        initialize_cloud()
    except DB_ERRORS:
        raise SystemExit("Setup gagal. Periksa SUPABASE_DB_URL, password, koneksi, dan izin membuat tabel.")
    print("Supabase terhubung. Tabel public.cuaca_online siap digunakan.")
