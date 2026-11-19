"""Prakiraan Open-Meteo untuk dashboard (WIB). Sinkronisasi riwayat ada di sinkron_riwayat.py."""
from datetime import datetime, timedelta
import json
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from ambil_data import CITIES
from kondisi import condition
from jsonaman import bersih

FORECAST = "https://api.open-meteo.com/v1/forecast"
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def fetch(url, city, **params):
    lat, lon = CITIES[city]
    query = urlencode(dict(latitude=lat, longitude=lon, timezone="Asia/Jakarta", **params))
    with urlopen(f"{url}?{query}", timeout=15) as response:
        return json.load(response)


def outlook(city):
    return fetch(FORECAST, city, forecast_days=8,
                 current="temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                 hourly="temperature_2m,precipitation_probability,weather_code",
                 daily="temperature_2m_min,temperature_2m_max,temperature_2m_mean,weather_code,"
                       "precipitation_probability_max,precipitation_sum,wind_speed_10m_max,sunrise,sunset")


def _kondisi(code):
    icon, label = condition(code)
    return {"ikon": icon, "label": label}


def _jam(value):
    text = str(value)[11:16]
    return text or None


def ringkasan(report, today):
    """Ubah respons outlook() menjadi isi /api/cuaca. Galat OSError/ValueError/KeyError/TypeError
    berarti respons tidak bisa dipakai, sama seperti tampilan sebelumnya."""
    stamp = datetime.fromisoformat(report["current"]["time"])
    days = pd.DataFrame(report["daily"]).set_index("time")
    hours = pd.DataFrame(report["hourly"]).set_index("time")
    hours.index = pd.to_datetime(hours.index)
    current = report["current"]
    day = days.loc[today.isoformat()]
    if stamp.date() != today:
        raise ValueError("Tanggal respons berbeda")

    now_hour = pd.Timestamp(stamp).floor("h")
    probability = hours.precipitation_probability
    per_jam = [{"jam": "Kini", "waktu": stamp.isoformat(timespec="minutes"), "suhu": current["temperature_2m"],
                "peluang": probability.get(now_hour), "kode": current["weather_code"],
                "kondisi": _kondisi(current["weather_code"])}]
    upcoming = hours.loc[hours.index > stamp]
    for moment, row in upcoming.head(24).iterrows():
        per_jam.append({"jam": f"{moment:%H:%M}", "waktu": moment.isoformat(), "suhu": row.temperature_2m,
                        "peluang": row.precipitation_probability, "kode": row.weather_code,
                        "kondisi": _kondisi(row.weather_code)})

    chance = upcoming.head(12).precipitation_probability.dropna()
    tips = None
    if not chance.empty and chance.max() >= 50:
        tips = {"jam": f"{chance.idxmax():%H:%M}", "peluang": chance.max()}

    future = days.reindex([(today + timedelta(days=n)).isoformat() for n in range(1, 8)])
    tujuh_hari = []
    for key, row in future.iterrows():
        date_ = datetime.fromisoformat(key)
        tujuh_hari.append({
            "tanggal": key, "hari": HARI[date_.weekday()], "tgl": f"{date_:%d/%m}",
            "kode": row.weather_code, "kondisi": _kondisi(row.weather_code),
            "min": row.temperature_2m_min, "maks": row.temperature_2m_max, "rerata": row.temperature_2m_mean,
            "peluang": row.precipitation_probability_max, "presipitasi": row.precipitation_sum,
            "angin_maks": row.wind_speed_10m_max})

    return bersih({
        "waktu": stamp.isoformat(timespec="minutes"),
        "sekarang": {
            "suhu": current["temperature_2m"], "terasa": current["apparent_temperature"],
            "kelembapan": current["relative_humidity_2m"], "angin": current["wind_speed_10m"],
            "kode": current["weather_code"], "kondisi": _kondisi(current["weather_code"]),
            "min": day.temperature_2m_min, "maks": day.temperature_2m_max,
            "terbit": _jam(day.sunrise), "terbenam": _jam(day.sunset)},
        "tips_hujan": tips, "per_jam": per_jam, "tujuh_hari": tujuh_hari})
