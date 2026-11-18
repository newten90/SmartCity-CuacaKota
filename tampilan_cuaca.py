"""Tampilan kondisi saat ini dan prakiraan model cuaca Open-Meteo."""
from datetime import datetime, timedelta
from html import escape

import pandas as pd
import streamlit as st

from cuaca_online import outlook

CONDITIONS = {
    0: ("☀️", "Cerah"), 1: ("🌤️", "Sebagian besar cerah"), 2: ("⛅", "Cerah berawan"),
    3: ("☁️", "Berawan"), 45: ("🌫️", "Berkabut"), 48: ("🌫️", "Kabut beku"),
    51: ("🌦️", "Gerimis ringan"), 53: ("🌦️", "Gerimis"), 55: ("🌧️", "Gerimis lebat"),
    61: ("🌦️", "Hujan ringan"), 63: ("🌧️", "Hujan sedang"), 65: ("🌧️", "Hujan lebat"),
    80: ("🌦️", "Hujan lokal ringan"), 81: ("🌧️", "Hujan lokal sedang"), 82: ("🌧️", "Hujan lokal lebat"),
    95: ("⛈️", "Badai petir"), 96: ("⛈️", "Petir dan hujan es"), 99: ("⛈️", "Petir dan hujan es lebat"),
}


def condition(code):
    return CONDITIONS.get(code, ("🌡️", "Kondisi belum tersedia"))


def fmt(value, unit, digits=0):
    return "—" if pd.isna(value) else f"{value:.{digits}f}{unit}"


@st.cache_data(ttl=900, show_spinner=False)
def weather(city, day):
    return outlook(city)


def show_weather(city, today):
    try:
        report = weather(city, today)
        stamp = datetime.fromisoformat(report["current"]["time"])
        days = pd.DataFrame(report["daily"]).set_index("time")
        hours = pd.DataFrame(report["hourly"]).set_index("time")
        hours.index = pd.to_datetime(hours.index)
        current = report["current"]
        day = days.loc[today.isoformat()]
        if stamp.date() != today:
            raise ValueError("Tanggal respons berbeda")
    except (OSError, ValueError, KeyError, TypeError):
        st.warning("Prakiraan Open-Meteo sedang tidak tersedia. Riwayat per jam tersedia di bawah.")
        return
    icon, label = condition(current["weather_code"])
    colors = ("#152e54", "#355582") if stamp.hour >= 18 or stamp.hour < 6 else ("#175882", "#407ba2")
    st.html(f"""<section style="background:radial-gradient(circle at 84% 24%,#dbeeff66 0 23px,transparent 25px),radial-gradient(ellipse at 82% 120%,#b8e3f255 0 23%,transparent 23.4%),radial-gradient(ellipse at 98% 115%,#93cce944 0 38%,transparent 38.3%),linear-gradient(115deg,{colors[0]},{colors[1]});color:white;
        border-radius:22px;padding:1.6rem 2rem;line-height:1.35">
        <div style="font-size:1.4rem;font-weight:600">{escape(city)}</div>
        <div style="font-size:clamp(3rem,6vw,4.8rem);letter-spacing:-.05em;font-weight:500">{fmt(current['temperature_2m'],'°',1)} {icon}</div>
        <strong>{label}</strong> · Terasa {fmt(current['apparent_temperature'],'°',1)}<br>
        Tertinggi {fmt(day.temperature_2m_max,'°',1)} · Terendah {fmt(day.temperature_2m_min,'°',1)}
        <div style="margin-top:.7rem;font-size:.9rem">Open-Meteo · {stamp:%d/%m/%Y %H:%M} WIB</div></section>""")
    for col, name, value in zip(st.columns(4),
            ["Kelembapan", "Angin", "Matahari terbit", "Matahari terbenam"],
            [fmt(current["relative_humidity_2m"], "%"), fmt(current["wind_speed_10m"], " km/j", 1),
             str(day.sunrise)[11:16] or "—", str(day.sunset)[11:16] or "—"]):
        col.metric(name, value, border=True)
    st.subheader("24 jam ke depan")
    st.caption("Waktu dalam WIB · Tetes air menunjukkan peluang hujan.")
    cards = []
    for ts, row in hours.loc[hours.index > stamp].head(24).iterrows():
        symbol, desc = condition(row.weather_code)
        cards.append(f'<div style="min-width:80px;text-align:center;padding:.6rem;border:1px solid #7399a94d;background:linear-gradient(160deg,#6aabba18,#79acc607);'
                     f'border-radius:12px"><small>{ts:%H:%M}</small><div title="{desc}">{symbol}</div>'
                     f'<strong>{fmt(row.temperature_2m,"°",1)}</strong><br><small>💧 {fmt(row.precipitation_probability,"%")}</small></div>')
    st.html('<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px">' + "".join(cards) + "</div>")
    st.subheader("Prakiraan 7 hari")
    future = days.reindex([(today + timedelta(days=n)).isoformat() for n in range(1, 8)])
    dates = pd.to_datetime(future.index)
    weekdays = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    table = pd.DataFrame({
        "Hari (WIB)": [f"{weekdays[d.weekday()]}, {d:%d/%m}" for d in dates],
        "Kondisi": [" ".join(condition(code)) for code in future.weather_code],
        "Min (°C)": future.temperature_2m_min, "Maks (°C)": future.temperature_2m_max,
        "Rerata (°C)": future.temperature_2m_mean, "Peluang hujan (%)": future.precipitation_probability_max,
        "Presipitasi (mm)": future.precipitation_sum, "Angin maks (km/j)": future.wind_speed_10m_max,
    })
    st.dataframe(table, hide_index=True, use_container_width=True)
