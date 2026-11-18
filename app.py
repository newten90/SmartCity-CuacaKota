from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from analisis import FIELDS, TEMP, RH, RAIN, PM, LABELS, NAMES, aggregate, load, monthly
from prediksi import MIN_HOURS, train, forecast
from penyimpanan import DB_ERRORS, WIB, session

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
analysis, prediction, replay = st.tabs(["Analisis 2025", "Prediksi suhu", "Simulasi sensor"])
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
    st.caption("Bandung · 1 Januari 2025 · Simulasi dari arsip per jam")
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
        readings = records.iloc[:n]
        row = readings.iloc[-1]
        st.subheader(f"Pengukuran pukul {int(row.jam):02d}.00 WIB")
        a, b = st.columns(2)
        a.metric("Suhu", f"{row[TEMP]:.1f} °C", border=True)
        b.metric("Kelembapan", f"{row[RH]:.0f} %", border=True)
        if n > 1:
            chart(readings, "jam", TEMP, "Perubahan suhu sejak tengah malam", "Jam (WIB)")
    else:
        st.info("Klik Data berikutnya untuk melihat pengukuran pukul 00.00 WIB.")
    if n==len(records): st.success("Seluruh catatan sudah ditampilkan.")
with replay:
    show_replay()


@st.cache_resource
def models():
    return train(dataset())


@st.fragment(run_every="60s")
def show_prediction():
    st.subheader("Prediksi suhu rata-rata 7 hari ke depan")
    city = st.selectbox("Kota prediksi", sorted(data.kota.unique()))
    today = datetime.now(WIB).date()
    yesterday = today - timedelta(days=1)
    observed = None
    try:
        with session() as store:
            temp, hours = store.daily_temperature(city, yesterday)
        if hours >= MIN_HOURS:
            observed = temp
            st.caption(f"Memakai arsip 2025 dan suhu kemarin di {city} ({hours} jam terukur, rata-rata {temp:.1f} °C).")
        else:
            st.caption(f"Estimasi dari pola musiman arsip 2025. Data kemarin mencakup {hours} dari minimal {MIN_HOURS} jam.")
    except DB_ERRORS:
        st.warning("Riwayat sensor belum bisa dibaca. Estimasi memakai pola musiman arsip 2025.")
    model, errors = models()[city]
    estimates = forecast(model, today, observed)
    frame = estimates.rename("Suhu rata-rata (°C)").rename_axis("Tanggal (WIB)").reset_index()
    frame["Tanggal (WIB)"] = frame["Tanggal (WIB)"].dt.strftime("%d/%m/%Y")
    st.dataframe(frame.round(1), hide_index=True, use_container_width=True)
    st.caption(f"Galat absolut rata-rata pada uji Oktober–Desember 2025 untuk {city}: "
               f"{errors[observed is not None]:.2f} °C (rata-rata seluruh horizon).")


with prediction:
    show_prediction()


st.caption("Data historis diolah dari Open-Meteo · cuaca ERA5 (ECMWF), kualitas udara Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo · CC BY 4.0. Satu titik model per kota.")
