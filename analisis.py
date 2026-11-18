from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
TEMP, RH, RAIN, PM = "temperature_2m", "relative_humidity_2m", "rain", "pm2_5"
FIELDS = [TEMP, RH, RAIN, PM]
LABELS = ["Suhu (°C)", "Kelembapan (%)", "Hujan (mm)", "PM2.5 (µg/m³)"]
NAMES = dict(zip(FIELDS, LABELS))

def load():
    return pd.read_csv(ROOT / "data/cuaca_udara.csv")

def aggregate(data, keys):
    groups = data.groupby(keys, sort=True)
    result = groups[FIELDS].mean()
    result[RAIN] = groups[RAIN].sum().where(groups[RAIN].count() == groups.size())
    return result.reset_index()

def monthly(data):
    result = aggregate(data, ["kota", "bulan"])
    month_days = pd.to_datetime(result.bulan + "-01").dt.days_in_month
    hours = data.groupby(["kota", "bulan"]).size().to_numpy()
    result["bulan_utuh"] = (hours == month_days * 24) & result[RAIN].notna()
    return result

if __name__ == "__main__":
    data = load()
    aggregate(data, ["kota", "tanggal"]).to_csv(ROOT/"data/harian.csv", index=False)
    monthly(data).to_csv(ROOT/"data/bulanan.csv", index=False)
