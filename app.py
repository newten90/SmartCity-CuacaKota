from contextlib import closing
from datetime import date, datetime, timedelta
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from analisis import FIELDS, TEMP, RH, RAIN, PM, LABELS, NAMES, aggregate, load, monthly
from prediksi import train, forecast
from sensor import WIB, connect

st.set_page_config(page_title="Cuaca Kota", layout="wide")
@st.cache_data
def dataset():
    return load()

def chart(frame, x, y, title, x_label, kind="line"):
    fig = getattr(px, kind)(frame, x=x, y=y, labels={**NAMES, x:x_label}, title=title,
                            color_discrete_sequence=["#08796f" if y in [RH, PM] else "#22689c"])
    fig.update_layout(height=290, margin=dict(t=46, b=8, l=8, r=8))
    st.plotly_chart(fig, use_container_width=True)

def correlation(frame, x, y):
    pairs = frame[[x,y]].dropna()
    r = pairs[x].corr(pairs[y]) if len(pairs)>1 and pairs.nunique().min()>1 else None
    return f"r = {r:.3f} · {len(pairs)} pasangan" if r is not None else f"Korelasi belum tersedia · {len(pairs)} pasangan"

data = dataset()
st.caption("TELEMATIKA  /  SMART CITY")
st.title("Cuaca dan udara perkotaan")
st.write("Bandung, Jakarta, dan Surabaya · Waktu Indonesia Barat")
analysis, replay, live = st.tabs(["Analisis 2025", "Simulasi sensor", "Sensor langsung"])
with analysis:
    c1,c2 = st.columns([1,2])
    city = c1.selectbox("Kota", sorted(data.kota.unique()))
    span = c2.date_input("Rentang tanggal (inklusif)", (date(2025,1,1),date(2025,12,31)),
                         min_value=date(2025,1,1), max_value=date(2025,12,31),format="DD/MM/YYYY")
    if len(span)!=2:
        st.info("Pilih tanggal akhir untuk menghitung ringkasan.")
    else:
        period = data[data.tanggal.between(*map(str,span))]
        selected = period[period.kota.eq(city)]
        comparison = aggregate(period, "kota")
        indicator = comparison.set_index("kota").loc[city]
        for col, field, label in zip(st.columns(4), FIELDS, LABELS):
            col.metric(("Total " if field==RAIN else "Rerata ")+label, f"{indicator[field]:.2f}" if pd.notna(indicator[field]) else "—")
        st.caption(f"{city} · {len(selected):,} interval jam · Nilai valid: " +
                   " / ".join(f"{name} {selected[f].count()}" for name,f in zip(["suhu","kelembapan","hujan","PM2.5"],FIELDS)) +
                   " · PM2.5 merupakan estimasi model.")
        daily = aggregate(selected, ["kota","tanggal"])
        month = monthly(selected)
        chart(daily,"tanggal",TEMP,"Suhu rata-rata harian","Tanggal")
        a,b = st.columns(2)
        with a: chart(month,"bulan",RAIN,"Jumlah hujan per bulan","Bulan", "bar")
        with b: chart(month,"bulan",PM,"Rerata PM2.5 per bulan","Bulan", "bar")
        if not month.bulan_utuh.all():
            st.info("Bulan parsial atau hujan tidak lengkap: " + ", ".join(month.loc[~month.bulan_utuh,"bulan"]) + ". Grafik memakai tanggal terpilih. Korelasi bulanan hanya memakai bulan utuh.")
        st.subheader("Perbandingan pada tanggal yang sama")
        st.dataframe(comparison.rename(columns=NAMES).round(2), hide_index=True,use_container_width=True)
        with st.expander("Hubungan antarvariabel"):
            chart(daily,TEMP,RH,"Suhu dan kelembapan harian",LABELS[0],"scatter")
            st.write(correlation(daily,TEMP,RH))
            complete = month[month.bulan_utuh]
            chart(complete,RAIN,PM,"Hujan dan PM2.5 bulanan",LABELS[2],"scatter")
            st.write(correlation(complete,RAIN,PM))
            st.caption("Korelasi Pearson menunjukkan arah hubungan dalam periode terpilih. Pola musiman dan faktor lain dapat memengaruhi keduanya.")
        st.download_button("Unduh CSV kota dan periode terpilih",selected.to_csv(index=False).encode(),f"{city}_{span[0]}_{span[1]}.csv","text/csv")
@st.fragment
def show_replay():
    st.subheader("Sensor virtual Bandung")
    st.write("Putar ulang 24 jam pertama pada 1 Januari 2025. Setiap klik mengambil satu catatan historis. Ringkasan pada tab Analisis tetap memakai arsip aslinya.")
    records = data[(data.kota=="Bandung") & (data.tanggal=="2025-01-01")].sort_values("jam")
    st.session_state.setdefault("pos",0)
    def advance():
        st.session_state.pos=min(len(records),st.session_state.pos+1)
    def reset():
        st.session_state.pos=0
    n=st.session_state.pos
    a,b=st.columns(2)
    a.button("Data berikutnya",on_click=advance,disabled=n>=len(records))
    b.button("Ulangi dari awal",on_click=reset)
    st.progress(n/len(records),text=f"{n} dari {len(records)} catatan")
    if n:
        row=records.iloc[n-1]
        st.json({"id_sensor":"BDG-V01","waktu_WIB":row.waktu,"suhu_C":row[TEMP],"kelembapan_persen":row[RH],"jenis":"simulasi historis"})
    if n==len(records): st.success("Seluruh catatan sudah ditampilkan.")
with replay:
    show_replay()


@st.cache_resource
def models():
    return train(dataset())


@st.fragment(run_every="5s")
def show_live():
    st.subheader("Pengukuran sensor")
    st.caption("Dashboard memeriksa kiriman baru setiap 5 detik.")
    try:
        with closing(connect()) as db:
            devices = [tuple(row) for row in db.execute("SELECT DISTINCT kota, sensor FROM readings ORDER BY kota, sensor")]
            if not devices:
                st.info("Menunggu kiriman pertama. Ikuti bagian Kirim data sensor di README untuk mencoba.")
                return
            city, device = st.selectbox("Perangkat", devices, format_func=lambda pair: " · ".join(pair))
            history = pd.read_sql_query(
                "SELECT waktu, suhu, kelembapan FROM readings WHERE kota=? AND sensor=? ORDER BY waktu DESC LIMIT 60",
                db, params=(city, device))
    except sqlite3.Error:
        st.error("Riwayat sensor belum bisa dibaca. Periksa lokasi dan izin tulis SENSOR_DB.")
        return
    row = history.iloc[0]
    stamp = datetime.fromisoformat(row.waktu)
    st.write(f"Pengukuran terakhir · {stamp:%d/%m/%Y %H:%M:%S} WIB")
    if datetime.now(WIB) - stamp > timedelta(minutes=5):
        st.warning("Sudah lebih dari 5 menit sejak pengukuran terakhir.")
    weights, mae, baseline = models()[city]
    target = stamp + timedelta(hours=1)
    a, b, c = st.columns(3)
    a.metric("Suhu terukur", f"{row.suhu:.1f} °C")
    b.metric("Kelembapan terukur", f"{row.kelembapan:.1f} %")
    c.metric(f"Prediksi suhu · {target:%d/%m %H:%M} WIB", f"{forecast(weights, row.suhu, row.kelembapan, stamp):.1f} °C")
    st.caption(f"Uji arsip {city}, Oktober–Desember 2025 · Rata-rata galat absolut model {mae:.2f} °C. "
               f"Jika suhu dianggap tetap, galatnya {baseline:.2f} °C.")
    st.dataframe(history.assign(waktu=history.waktu.map(lambda value: datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M:%S")))
                 .rename(columns={"waktu":"Waktu (WIB)", "suhu":"Suhu (°C)", "kelembapan":"Kelembapan (%)"}),
                 hide_index=True, use_container_width=True)


with live:
    show_live()
st.caption("Data historis diolah dari Open-Meteo · cuaca ERA5 (ECMWF), kualitas udara Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo · CC BY 4.0. Satu titik model per kota.")
