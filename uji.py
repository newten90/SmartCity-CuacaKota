"""Pemeriksaan yang bisa diulangi dari folder proyek: python uji.py
Tanpa internet dan tanpa database asli."""
import os
os.environ["SUPABASE_DB_URL"] = ""  # jangan sentuh Supabase asli saat menguji
from datetime import date
from unittest.mock import patch
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import pandas as pd
from fastapi.testclient import TestClient
from analisis import FIELDS, RAIN, aggregate, load, monthly, ROOT
import main

d = load()
assert len(d) == 26280 and not d.duplicated(["kota", "waktu"]).any()
assert d[FIELDS].isna().sum().sum() == 0
client = TestClient(main.app)
results = []
for city in sorted(d.kota.unique()):
    for start, end in [("2025-01-01", "2025-12-31"), ("2025-02-10", "2025-02-16"), ("2025-08-01", "2025-08-01"),
                       ("2025-12-20", "2025-12-31")]:
        response = client.get("/api/analisis", params=dict(kota=city, dari=start, sampai=end))
        assert response.status_code == 200, (city, start, end, response.text)
        indicators = response.json()["indikator"]
        part = d[(d.kota == city) & d.tanggal.between(start, end)]
        for f in FIELDS:
            ref = part[f].sum() if f == RAIN else part[f].mean()
            value = f"{indicators[f]:.2f}"
            assert value == f"{ref:.2f}", (city, f, value, ref)
            results.append([city, start, end, f, value, f"{ref:.2f}", "sesuai"])
assert len(results) == 48
pd.DataFrame(results, columns=["kota", "awal", "akhir", "variabel", "dashboard", "pandas", "hasil"]).to_csv(
    ROOT / "bukti/uji_indikator.csv", index=False)

# Hujan kosong: total hujan null dan bulan tidak utuh, juga lewat endpoint.
sample = d.iloc[:24].copy()
sample.loc[sample.index[0], RAIN] = float("nan")
assert pd.isna(aggregate(sample, "tanggal").iloc[0][RAIN])
assert not monthly(sample).bulan_utuh.any()
with patch("layanan.dataset", return_value=sample):
    body = client.get("/api/analisis", params=dict(kota="Bandung", dari="2025-01-01", sampai="2025-01-01")).json()
assert body["indikator"][RAIN] is None and body["kartu"]["hujan"]["nilai"] is None
assert body["harian"][0][RAIN] is None
assert [month["bulan_utuh"] for month in body["bulanan"]] == [False]
assert "2025-01" in body["bulan_parsial"]
print("Lulus: 48 nilai indikator, data hujan kosong.")
