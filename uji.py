"""Pemeriksaan yang bisa diulangi dari folder proyek."""
from streamlit.testing.v1 import AppTest
from datetime import date
from pathlib import Path
import pandas as pd
from analisis import FIELDS, RAIN, aggregate, load, monthly, ROOT
d=load()
assert len(d)==26280 and not d.duplicated(["kota","waktu"]).any()
assert d[FIELDS].isna().sum().sum()==0
app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=35).run()
results=[]
for city in sorted(d.kota.unique()):
    app.tabs[1].selectbox[0].select(city)
    for start,end in [("2025-01-01","2025-12-31"),("2025-02-10","2025-02-16"),("2025-08-01","2025-08-01"),("2025-12-20","2025-12-31")]:
        app.date_input[0].set_value((date.fromisoformat(start),date.fromisoformat(end))).run()
        assert not app.exception
        part=d[(d.kota==city)&d.tanggal.between(start,end)]
        for metric,f in zip(app.tabs[1].metric,FIELDS):
            ref=part[f].sum() if f==RAIN else part[f].mean()
            assert metric.value==f"{ref:.2f}", (city,f,metric.value,ref)
            results.append([city,start,end,f,metric.value,f"{ref:.2f}","sesuai"])
pd.DataFrame(results,columns=["kota","awal","akhir","variabel","dashboard","pandas","hasil"]).to_csv(ROOT/"bukti/uji_indikator.csv",index=False)
for i in range(24):
    app.button[0].click().run()
    assert app.session_state["pos"]==i+1
assert app.button[0].disabled
app.button[1].click().run()
assert app.session_state["pos"]==0 and not app.button[0].disabled
sample=d.iloc[:24].copy()
sample.loc[sample.index[0],RAIN]=float("nan")
assert pd.isna(aggregate(sample,"tanggal").iloc[0][RAIN])
assert not monthly(sample).bulan_utuh.any()
print("Lulus: 48 nilai indikator, 24 langkah simulasi, batas akhir, reset, data hujan kosong.")
