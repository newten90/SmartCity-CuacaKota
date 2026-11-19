"""Membaca berkas .env sederhana (KUNCI=nilai) ke os.environ untuk pemakaian lokal.
Variabel yang sudah ada di lingkungan tidak ditimpa. Berkas .env tidak masuk repositori."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def muat_env(path=ROOT / ".env"):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)
