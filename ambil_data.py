"""Jalankan dari direktori proyek. Arsip JSON menyimpan parameter dan hasil asli."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

CITIES = {"Bandung": (-6.9175,107.6191), "Jakarta": (-6.2088,106.8456), "Surabaya": (-7.2575,112.7521)}
SOURCES = {"cuaca": ("https://archive-api.open-meteo.com/v1/archive", "temperature_2m,relative_humidity_2m,rain"), "udara": ("https://air-quality-api.open-meteo.com/v1/air-quality","pm2_5")}
ROOT = Path(__file__).resolve().parent / "data"

def download(task):
    city, source = task
    url, fields = SOURCES[source]
    lat, lon = CITIES[city]
    params = dict(latitude=lat, longitude=lon,start_date="2025-01-01",end_date="2025-12-31",timezone="Asia/Jakarta",hourly=fields)
    if source == "cuaca":
        params["models"] = "era5"
    url += "?" + urlencode(params)
    path = ROOT / f"{city}_{source}.json"
    try:
        with urlopen(url, timeout=60) as response:
            raw = json.load(response)
        frame = pd.DataFrame(raw["hourly"]).set_index("time")
        path.write_text(json.dumps(dict(url=url, retrieved_utc=datetime.now(timezone.utc).isoformat(),response=raw)),encoding="utf-8")
    except Exception:
        if not path.exists():
            raise
        print("Menggunakan arsip", path.name)
        frame = pd.DataFrame(json.loads(path.read_text())["response"]["hourly"]).set_index("time")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.has_duplicates:
        raise ValueError(f"Waktu duplikat: {city} {source}")
    return city,source,frame

def main():
    tasks = [(c,s) for c in CITIES for s in SOURCES]
    with ThreadPoolExecutor(6) as pool:
        datasets = {(c,s):f for c,s,f in pool.map(download,tasks)}
    rows = []
    for c in CITIES:
        f = pd.concat([datasets[c,s] for s in SOURCES],axis=1).reindex(pd.date_range("2025-01-01",periods=8760,freq="h")).apply(pd.to_numeric,errors="coerce")
        f.loc[~f.relative_humidity_2m.between(0,100),"relative_humidity_2m"] = None
        for col in ["rain","pm2_5"]:
            f.loc[f[col]<0,col] = None
        f.insert(0,"kota",c)
        f.index.name="waktu"
        rows.append(f.reset_index())
    data=pd.concat(rows,ignore_index=True)
    data["tanggal"]=data.waktu.dt.date
    data["bulan"]=data.waktu.dt.strftime("%Y-%m")
    data["jam"]=data.waktu.dt.hour
    data.to_csv(ROOT/"cuaca_udara.csv",index=False)
    print(data.groupby("kota").count())
if __name__=="__main__":
    main()
