from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from analisis import FIELDS, TEMP, RH, RAIN, PM, LABELS, NAMES, aggregate, load, monthly

st.set_page_config(page_title="Cuaca Kota • 2025", layout="wide")
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
st.caption("TELEMATIKA  /  SMART CITY     •     ARSIP 2025")
st.title("Cuaca dan udara perkotaan")
st.write("Bandung, Jakarta, dan Surabaya · Data per jam dalam WIB")
analysis, replay = st.tabs(["Analisis", "Simulasi sensor"])
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
st.caption("Data historis diolah dari Open-Meteo · cuaca ERA5 (ECMWF), kualitas udara Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo · CC BY 4.0. Satu titik model per kota.")
