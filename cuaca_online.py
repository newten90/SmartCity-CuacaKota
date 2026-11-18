"""Sinkronisasi riwayat per jam dan prakiraan Open-Meteo (WIB)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import urlopen
import json

import pandas as pd

from ambil_data import CITIES
from analisis import TEMP, RH, PM, ROOT
from penyimpanan import WIB, session, initialize_cloud

START = date(2026, 10, 1)
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER = [TEMP, RH, "precipitation", "wind_speed_10m", "weather_code"]
SNAPSHOT = ROOT / "data/riwayat_online.csv"
COLS = ["kota", "waktu", *WEATHER, PM, "sumber"]


def fetch(url, city, **params):
    lat, lon = CITIES[city]
    query = urlencode(dict(latitude=lat, longitude=lon, timezone="Asia/Jakarta", **params))
    with urlopen(f"{url}?{query}", timeout=15) as response:
        return json.load(response)


def hourly(url, city, start, end, fields, **params):
    result = fetch(url, city, start_date=start, end_date=end, hourly=",".join(fields), **params)
    frame = pd.DataFrame(result["hourly"]).set_index("time")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.has_duplicates:
        raise ValueError(f"Timestamp ganda untuk {city}")
    return frame


def city_history(city, now):
    # ERA5 memerlukan beberapa hari sebelum tersedia. Untuk minggu terakhir
    # ambil interval yang sudah lewat dari model operasional.
    change = now.date() - timedelta(days=6)
    chunks = []
    start = START
    while start <= now.date():
        archive = start < change
        limit = change - timedelta(days=1) if archive else now.date()
        end = min(start + timedelta(days=30), limit)
        frame = hourly(ARCHIVE if archive else FORECAST, city, start, end, WEATHER,
                       **({"models": "era5"} if archive else {}))
        frame[PM] = hourly(AIR, city, start, end, [PM])[PM]
        frame["sumber"] = "Open-Meteo ERA5" if archive else "Open-Meteo Best Match"
        chunks.append(frame)
        start = end + timedelta(days=1)
    frame = pd.concat(chunks)
    last = pd.Timestamp(now).tz_convert(WIB).tz_localize(None).floor("h")
    frame = frame.reindex(pd.date_range(START, last, freq="h"))
    if frame[WEATHER].isna().any().any():
        raise ValueError(f"Riwayat cuaca belum lengkap untuk {city}.")
    frame["kota"] = city
    frame.index.name = "waktu"
    return frame.reset_index()[COLS]


def outlook(city):
    return fetch(FORECAST, city, forecast_days=8,
                 current="temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                 hourly="temperature_2m,precipitation_probability,weather_code",
                 daily="temperature_2m_min,temperature_2m_max,temperature_2m_mean,weather_code,"
                       "precipitation_probability_max,precipitation_sum,wind_speed_10m_max,sunrise,sunset")


def sync():
    now = datetime.now(WIB)
    with ThreadPoolExecutor(3) as pool:
        frames = list(pool.map(lambda city: city_history(city, now), CITIES))
    history = pd.concat(frames, ignore_index=True)
    initialize_cloud()
    records = history.copy()
    records["waktu"] = records.waktu.dt.tz_localize(WIB)
    records = records.astype(object).where(records.notna(), None)
    with session() as store:
        with store.db.cursor() as cursor:
            cursor.executemany("""INSERT INTO public.cuaca_online
                (kota,waktu,temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code,pm2_5,sumber)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (kota,waktu) DO UPDATE SET
                temperature_2m=excluded.temperature_2m,relative_humidity_2m=excluded.relative_humidity_2m,
                precipitation=excluded.precipitation,wind_speed_10m=excluded.wind_speed_10m,
                weather_code=excluded.weather_code,pm2_5=excluded.pm2_5,sumber=excluded.sumber""",
                records.itertuples(index=False, name=None))
    with NamedTemporaryFile(dir=SNAPSHOT.parent, suffix=".tmp", mode="w", encoding="utf-8",
                            newline="", delete=False) as tmp:
        history.to_csv(tmp, index=False)
    Path(tmp.name).replace(SNAPSHOT)
    print(history.groupby("kota").waktu.agg(["min", "max", "count"]))


if __name__ == "__main__":
    sync()
