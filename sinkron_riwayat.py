"""Sinkronisasi riwayat per jam Open-Meteo ke Supabase (WIB).

    python sinkron_riwayat.py            # inkremental: ambil ulang ~10 hari terakhir
    python sinkron_riwayat.py --penuh    # impor ulang sejak 1 Oktober 2026
    python sinkron_riwayat.py --csv      # dari laptop: perbarui juga data/riwayat_online.csv

Prakiraan untuk dashboard ada di prakiraan.py."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from ambil_data import CITIES
from analisis import TEMP, RH, PM, ROOT
from penyimpanan import DB_ERRORS, WIB, session, initialize_cloud
from prakiraan import FORECAST, fetch

START = date(2026, 10, 1)
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER = [TEMP, RH, "precipitation", "wind_speed_10m", "weather_code"]
SNAPSHOT = ROOT / "data/riwayat_online.csv"
COLS = ["kota", "waktu", *WEATHER, PM, "sumber"]
RIWAYAT_SQL = """SELECT kota,waktu AT TIME ZONE 'Asia/Jakarta',
    temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code,pm2_5,sumber
    FROM public.cuaca_online ORDER BY kota,waktu"""
ERA5_TUNDA = 6      # ERA5 baru tersedia beberapa hari kemudian
TUMPANG = 10        # sinkron inkremental mengambil ulang sekian hari terakhir
POTONGAN = 30       # hari per permintaan


def hourly(url, city, start, end, fields, **params):
    result = fetch(url, city, start_date=start, end_date=end, hourly=",".join(fields), **params)
    frame = pd.DataFrame(result["hourly"]).set_index("time")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.has_duplicates:
        raise ValueError(f"Timestamp ganda untuk {city}")
    return frame


def potong(start, today):
    """Bagi rentang start..today menjadi (arsip, awal, akhir). Tanggal sebelum today-6 memakai ERA5,
    sisanya model operasional, dan satu potongan tidak melebihi 31 hari."""
    change = today - timedelta(days=ERA5_TUNDA)
    chunks = []
    while start <= today:
        archive = start < change
        limit = change - timedelta(days=1) if archive else today
        end = min(start + timedelta(days=POTONGAN), limit)
        chunks.append((archive, start, end))
        start = end + timedelta(days=1)
    return chunks


def mulai(terakhir, today):
    """Awal pengambilan ulang: ~10 hari terakhir, atau sejak data terakhir bila sinkron sempat berhenti lebih lama."""
    if terakhir is None:
        return START
    return max(START, min(today - timedelta(days=TUMPANG), terakhir.date()))


def city_history(city, now, start=START):
    """Kembalikan (baris lengkap, jam kosong). Jam yang cuacanya kosong tidak disimpan dan tidak menggagalkan sinkron."""
    chunks = []
    for archive, first, last_day in potong(start, now.date()):
        frame = hourly(ARCHIVE if archive else FORECAST, city, first, last_day, WEATHER,
                       **({"models": "era5"} if archive else {}))
        frame[PM] = hourly(AIR, city, first, last_day, [PM])[PM]
        frame["sumber"] = "Open-Meteo ERA5" if archive else "Open-Meteo Best Match"
        chunks.append(frame)
    frame = pd.concat(chunks)
    last = pd.Timestamp(now).tz_convert(WIB).tz_localize(None).floor("h")
    frame = frame.reindex(pd.date_range(pd.Timestamp(start), last, freq="h"))
    empty = frame[WEATHER].isna().any(axis=1)
    missing = list(frame.index[empty])
    frame = frame[~empty].copy()
    frame["weather_code"] = frame.weather_code.astype(int)
    frame["kota"] = city
    frame.index.name = "waktu"
    return frame.reset_index()[COLS], missing


def _fetch_city(city, now, start):
    try:
        frame, missing = city_history(city, now, start)
        return city, frame, missing, None
    except (OSError, ValueError, KeyError) as exc:
        return city, None, [], f"{type(exc).__name__}: {exc}"


def _write_csv(frame):
    with NamedTemporaryFile(dir=SNAPSHOT.parent, suffix=".tmp", mode="w", encoding="utf-8",
                            newline="", delete=False) as tmp:
        frame.to_csv(tmp, index=False)
    Path(tmp.name).replace(SNAPSHOT)


def sync(penuh=False, csv=False, now=None):
    """Simpan riwayat ke Supabase dan kembalikan ringkasan per kota."""
    now = now or datetime.now(WIB)
    initialize_cloud()
    last_seen = {}
    if not penuh:
        with session() as db:
            last_seen = dict(db.execute(
                "SELECT kota, max(waktu AT TIME ZONE 'Asia/Jakarta') FROM public.cuaca_online GROUP BY kota").fetchall())
    starts = {city: START if penuh else mulai(last_seen.get(city), now.date()) for city in CITIES}
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(lambda city: _fetch_city(city, now, starts[city]), CITIES))

    summary = {}
    frames = []
    for city, frame, missing, error in results:
        summary[city] = {"awal": starts[city].isoformat(), "kosong": [f"{m:%Y-%m-%d %H:%M}" for m in missing],
                         "galat": error, "disimpan": 0, "akhir": None}
        if frame is not None and not frame.empty:
            summary[city].update(disimpan=len(frame), akhir=f"{frame.waktu.max():%Y-%m-%d %H:%M}")
            frames.append(frame)
    if frames:
        history = pd.concat(frames, ignore_index=True)
        records = history.copy()
        records["waktu"] = records.waktu.dt.tz_localize(WIB)
        records = records.astype(object).where(records.notna(), None)
        with session() as db:
            with db.cursor() as cursor:
                cursor.executemany("""INSERT INTO public.cuaca_online
                    (kota,waktu,temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code,pm2_5,sumber)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (kota,waktu) DO UPDATE SET
                    temperature_2m=excluded.temperature_2m,relative_humidity_2m=excluded.relative_humidity_2m,
                    precipitation=excluded.precipitation,wind_speed_10m=excluded.wind_speed_10m,
                    weather_code=excluded.weather_code,pm2_5=excluded.pm2_5,sumber=excluded.sumber""",
                    records.itertuples(index=False, name=None))
            if csv:
                _write_csv(pd.DataFrame(db.execute(RIWAYAT_SQL).fetchall(), columns=COLS))
    return summary


def tampilkan(summary):
    for city, item in summary.items():
        if item["galat"]:
            print(f"{city}: GAGAL diambil ({item['galat']})")
            continue
        print(f"{city}: {item['disimpan']} jam disimpan, dari {item['awal']} sampai {item['akhir']} WIB")
        if item["kosong"]:
            shown = ", ".join(item["kosong"][:10]) + (" ..." if len(item["kosong"]) > 10 else "")
            print(f"  {len(item['kosong'])} jam kosong dan dilewati: {shown}")


if __name__ == "__main__":
    from lingkungan import muat_env
    muat_env()
    parser = argparse.ArgumentParser(description="Sinkronkan riwayat per jam Open-Meteo ke Supabase.")
    parser.add_argument("--penuh", action="store_true", help="impor ulang sejak 1 Oktober 2026, bukan 10 hari terakhir")
    parser.add_argument("--csv", action="store_true", help="perbarui juga data/riwayat_online.csv (hanya dari laptop)")
    args = parser.parse_args()
    try:
        result = sync(args.penuh, args.csv)
    except ValueError as exc:
        raise SystemExit(str(exc))
    except DB_ERRORS:
        raise SystemExit("Sinkron gagal. Periksa SUPABASE_DB_URL, koneksi, dan izin tabel.")
    tampilkan(result)
    if any(item["galat"] for item in result.values()):
        raise SystemExit(1)
