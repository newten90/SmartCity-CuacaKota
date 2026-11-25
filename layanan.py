"""Logika di balik endpoint dashboard. Perhitungan memakai analisis.py, penyimpanan.py, dan sensor.py apa adanya."""
from datetime import date, datetime, timedelta
from functools import lru_cache
from http.client import HTTPException
import hmac
import json
import os
import re
import time

import pandas as pd

from ambil_data import CITIES
from analisis import FIELDS, TEMP, RH, RAIN, PM, NAMES, aggregate, load, monthly, pearson, correlation
from jsonaman import bersih
from penyimpanan import DB_ERRORS, WIB, cloud_url, session
from prakiraan import outlook, ringkasan
from sensor import measurement
from sinkron_riwayat import COLS, RIWAYAT_SQL, SNAPSHOT

KOTA = list(CITIES)
TAHUN_AWAL, TAHUN_AKHIR = date(2025, 1, 1), date(2025, 12, 31)
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]
AKTIF_MENIT = 15
USANG_JAM = 6
BATAS_BADAN = 4096
PESAN_PRAKIRAAN = "Prakiraan Open-Meteo sedang tidak tersedia. Riwayat per jam tersedia di bawah."
SUMBER_CSV = "salinan impor di repositori"


class Galat(Exception):
    def __init__(self, status, pesan):
        super().__init__(pesan)
        self.status, self.pesan = status, pesan


# ---------- cache sederhana dalam proses (pelengkap Cache-Control di main.py) ----------
_CACHE = {}


def _cache_get(key):
    item = _CACHE.get(key)
    return item[1] if item and item[0] > time.monotonic() else None


def _cache_put(key, value, ttl):
    _CACHE[key] = (time.monotonic() + ttl, value)


def bersihkan_cache():
    _CACHE.clear()


# ---------- validasi ----------
def cek_kota(kota):
    if kota is None:
        return KOTA[0]
    if kota not in CITIES:
        raise Galat(400, f"Kota tidak dikenal. Pilih {', '.join(KOTA[:-1])}, atau {KOTA[-1]}.")
    return kota


def _tanggal(teks):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", teks):
        raise Galat(400, f"Tanggal '{teks}' harus berformat YYYY-MM-DD, misalnya 2025-01-31.")
    try:
        value = date.fromisoformat(teks)
    except ValueError:
        raise Galat(400, f"Tanggal '{teks}' tidak valid.") from None
    if not TAHUN_AWAL <= value <= TAHUN_AKHIR:
        raise Galat(400, f"Tanggal '{teks}' di luar 2025. Pilih antara 2025-01-01 dan 2025-12-31.")
    return value


def cek_rentang(dari, sampai):
    dari, sampai = dari or None, sampai or None
    if dari is None and sampai is None:
        return TAHUN_AWAL.isoformat(), TAHUN_AKHIR.isoformat()
    if sampai is None:
        raise Galat(400, "Pilih tanggal akhir untuk menghitung ringkasan.")
    if dari is None:
        raise Galat(400, "Pilih tanggal awal untuk menghitung ringkasan.")
    start, end = _tanggal(dari), _tanggal(sampai)
    if start > end:
        raise Galat(400, "Tanggal awal tidak boleh setelah tanggal akhir.")
    return start.isoformat(), end.isoformat()


def pastikan_penyimpanan():
    """Di Vercel berkas proyek tidak bisa ditulis, jadi tanpa Supabase tidak ada penyimpanan sensor."""
    if os.getenv("VERCEL") and not cloud_url():
        raise Galat(503, "Penyimpanan sensor belum diatur. Isi SUPABASE_DB_URL (URI Session pooler Supabase) "
                         "di Environment Variables Vercel, lalu deploy ulang.")


# ---------- format angka Indonesia ----------
def angka(value, digits=2):
    if value is None or pd.isna(value):
        return "—"
    text = f"{abs(value):,.{digits}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return ("−" if value < 0 and round(abs(value), digits) != 0 else "") + text


# ---------- analisis 2025 ----------
@lru_cache(maxsize=1)
def dataset():
    return load()


def _bulan(code):
    return BULAN[int(code[5:7]) - 1]


def _ekstrem(month, kota):
    """Bulan terbasah dan terkering dari bulan utuh milik satu kota."""
    full = month[(month.kota == kota) & month.bulan_utuh & month[RAIN].notna()]
    if full.empty:
        return None, None
    wet, dry = full.loc[full[RAIN].idxmax()], full.loc[full[RAIN].idxmin()]
    return ({"kode": wet.bulan, "bulan": _bulan(wet.bulan), "hujan": wet[RAIN]},
            {"kode": dry.bulan, "bulan": _bulan(dry.bulan), "hujan": dry[RAIN]})


def _gabung(names):
    return " dan ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + ", dan " + names[-1]


def _kelompok(items):
    groups = {}
    for name, month in items.items():
        groups.setdefault(month, []).append(name)
    return groups


def _temuan(kota, rows, r_suhu, n_suhu):
    """Kalimat temuan disusun dari angka periode terpilih, bukan ditulis manual."""
    dry = _kelompok({row["kota"]: row["terkering"]["bulan"] for row in rows if row["terkering"]})
    wet = _kelompok({row["kota"]: row["terbasah"]["bulan"] for row in rows if row["terbasah"]})
    where = lambda names: "ketiga kota" if len(names) == len(KOTA) else _gabung(names)
    listing = lambda title, groups: title + ", ".join(f"{_gabung(names)} {month}" for month, names in groups.items())
    first = second = ""
    if len(dry) == 1:
        month, names = next(iter(dry.items()))
        first = f"{month} jadi bulan terkering di {where(names)}"
    elif dry:
        first = listing("Bulan terkering: ", dry)
    if len(wet) == 1:
        month, names = next(iter(wet.items()))
        second = f"{month} jadi bulan terbasah di {where(names)}"
    elif wet and len(dry) == 1 and any(len(names) > 1 for names in wet.values()):
        minor = [(month, names) for month, names in wet.items() if len(names) == min(map(len, wet.values()))]
        second = "tapi puncak hujan " + "; ".join(f"{_gabung(names)} ada di {month}" for month, names in minor)
    elif wet:
        second = listing("Puncak hujan: ", wet)
    parts = []
    if first and second.startswith("tapi"):
        parts.append(f"{first}, {second}.")
    else:
        parts.extend(f"{text}." for text in (first, second) if text)
    if r_suhu is not None:
        text = f"{angka(r_suhu, 3)}, {n_suhu} hari"
        if abs(r_suhu) < 0.3:
            parts.append(f"Hubungan suhu dan kelembapan harian di {kota} lemah (r = {text}).")
        else:
            trend = "lebih kering" if r_suhu < 0 else "lebih lembap"
            parts.append(f"Di {kota}, hari yang lebih hangat cenderung {trend} (r = {text}).")
    return " ".join(parts) or None


def _catatan_korelasi(rows):
    pairs = [(row["kota"], row["r_hujan_pm25"]) for row in rows if row["r_hujan_pm25"]["r"] is not None]
    if len(pairs) < 2:
        return None
    count = max(item["n"] for _, item in pairs)
    signs = {item["r"] > 0 for _, item in pairs}
    if len(signs) > 1:
        return (f"{count} pasangan bulan per kota dengan arah berbeda belum cukup untuk menyimpulkan "
                "hujan menyebabkan perubahan PM2.5.")
    return (f"Arah hubungan hujan dan PM2.5 sama di semua kota ({count} pasangan bulan per kota), "
            "tetapi korelasi tidak membuktikan sebab-akibat.")


def analisis(kota, dari, sampai):
    data = dataset()
    period = data[data.tanggal.between(dari, sampai)]
    selected = period[period.kota.eq(kota)]
    comparison = aggregate(period, "kota")
    indicator = comparison.set_index("kota").loc[kota]
    daily = aggregate(selected, ["kota", "tanggal"])
    month = monthly(selected)
    month_all = monthly(period)

    rows = []
    for _, row in comparison.iterrows():
        wet, dry = _ekstrem(month_all, row.kota)
        complete = month_all[(month_all.kota == row.kota) & month_all.bulan_utuh]
        r, n = pearson(complete, RAIN, PM)
        rows.append({"kota": row.kota, "terpilih": row.kota == kota, **{f: row[f] for f in FIELDS},
                     "terbasah": wet, "terkering": dry, "r_hujan_pm25": {"r": r, "n": n}})
    wet, dry = _ekstrem(month, kota)

    others = comparison[comparison.kota != kota]
    warmest = others.loc[others[TEMP].idxmax()] if not others.empty else None
    note_temp = None
    if warmest is not None:
        note_temp = (f"{angka(warmest[TEMP] - indicator[TEMP])} °C lebih sejuk dari {warmest.kota}"
                     if warmest[TEMP] > indicator[TEMP] else "terpanas dari tiga kota")
    note_rain = None
    rains = comparison[RAIN].dropna()
    if pd.notna(indicator[RAIN]) and len(rains) == len(KOTA):
        note_rain = ("terbanyak dari tiga kota" if indicator[RAIN] == rains.max() else
                     "tersedikit dari tiga kota" if indicator[RAIN] == rains.min() else "di tengah dari tiga kota")

    r_suhu, n_suhu = pearson(daily, TEMP, RH)
    complete = month[month.bulan_utuh]
    partial = month.loc[~month.bulan_utuh, "bulan"]
    return bersih({
        "kota": kota, "dari": dari, "sampai": sampai, "jam": len(selected),
        "indikator": {f: indicator[f] for f in FIELDS},
        "valid": {f: int(selected[f].count()) for f in FIELDS},
        "kartu": {"suhu": {"nilai": indicator[TEMP], "catatan": note_temp},
                  "hujan": {"nilai": indicator[RAIN], "catatan": note_rain},
                  "terbasah": wet, "terkering": dry},
        "harian": daily.drop(columns="kota"),
        "bulanan": month.drop(columns="kota"),
        "tabel_kota": rows,
        "korelasi": {
            "suhu_kelembapan": {"r": r_suhu, "n": n_suhu, "teks": correlation(daily, TEMP, RH)},
            "hujan_pm25": {**dict(zip(("r", "n"), pearson(complete, RAIN, PM))), "teks": correlation(complete, RAIN, PM)}},
        "catatan_korelasi": _catatan_korelasi(rows),
        "bulan_parsial": (
            "Bulan parsial atau hujan tidak lengkap: " + ", ".join(partial) +
            ". Grafik memakai tanggal terpilih. Korelasi bulanan hanya memakai bulan utuh.") if len(partial) else None,
        "temuan": _temuan(kota, rows, r_suhu, n_suhu)})


def analisis_csv(kota, dari, sampai):
    data = dataset()
    period = data[data.tanggal.between(dari, sampai)]
    selected = period[period.kota.eq(kota)]
    return selected.to_csv(index=False), f"{kota}_{dari}_{sampai}.csv"


# ---------- riwayat per jam ----------
def online_history():
    """Riwayat dari Supabase, atau salinan CSV di repositori bila database kosong/tidak terjangkau."""
    cached = _cache_get("riwayat")
    if cached is not None:
        return cached
    if cloud_url():
        try:
            with session() as store:
                if store.cloud:
                    rows = store.db.execute(RIWAYAT_SQL).fetchall()
                    if rows:
                        result = (pd.DataFrame(rows, columns=COLS), "Supabase")
                        _cache_put("riwayat", result, 900)
                        return result
        except DB_ERRORS:
            pass
    result = (pd.read_csv(SNAPSHOT, parse_dates=["waktu"]), SUMBER_CSV)
    _cache_put("riwayat", result, 60)
    return result


def _riwayat_kota(kota):
    history, source = online_history()
    history = history.assign(tanggal=history.waktu.dt.strftime("%Y-%m-%d"))
    return history[history.kota == kota], source


def riwayat_csv(kota):
    local, _ = _riwayat_kota(kota)
    return local.to_csv(index=False), f"{kota}_riwayat_online.csv"


def pola_jam(local, arsip):
    """Bandingkan jam WIB dengan tanggal kalender yang sama satu tahun sebelumnya."""
    kolom = [TEMP, RH, PM]
    kini = local.loc[local.waktu.dt.year.eq(2026), ["waktu", *kolom]].set_index("waktu")
    if kini.empty:
        return None
    dulu = arsip.set_index(pd.to_datetime(arsip.waktu))[kolom]
    sejajar = dulu.reindex(kini.index - pd.DateOffset(years=1))
    sejajar.index = kini.index
    hasil = {}
    for nama in kolom:
        pasangan = pd.concat([sejajar[nama], kini[nama]], axis=1, keys=["arsip", "riwayat"]).dropna()
        grup = pasangan.groupby(pasangan.index.hour)
        jam = grup.mean().reindex(range(24))
        jam["pasangan"] = grup.size().reindex(range(24), fill_value=0)
        jam["selisih"] = jam.riwayat - jam.arsip
        hasil[nama] = {"jam": jam.rename_axis("jam").reset_index(), "pasangan": len(pasangan),
                       "arsip": pasangan.arsip.mean(), "riwayat": pasangan.riwayat.mean(),
                       "selisih": (pasangan.riwayat - pasangan.arsip).mean()}
    return {"awal": kini.index.min(), "akhir": kini.index.max(), "variabel": hasil}


def riwayat(kota, now=None, terbaru=None):
    now = now or datetime.now(WIB)
    local, source = _riwayat_kota(kota)
    local = local.sort_values("waktu")
    last = local.waktu.max() if len(local) else None
    age = None if last is None else (now.replace(tzinfo=None) - last.to_pydatetime()).total_seconds() / 3600
    if source == "Supabase":
        note = None
    elif cloud_url():
        note = "Supabase tidak terjangkau. Menampilkan salinan impor di repositori (data/riwayat_online.csv)."
    else:
        note = ("Supabase belum dikonfigurasi (SUPABASE_DB_URL kosong). "
                "Menampilkan salinan impor di repositori (data/riwayat_online.csv).")
    shown = local.tail(terbaru) if terbaru else local
    rows = shown.drop(columns=["kota", "tanggal"]).assign(waktu=shown.waktu.dt.strftime("%Y-%m-%dT%H:%M"))
    return bersih({
        "kota": kota, "sumber_data": source, "tabel": "public.cuaca_online" if source == "Supabase" else "data/riwayat_online.csv",
        "catatan": note, "jumlah": len(local),
        "awal": None if last is None else f"{local.waktu.min():%Y-%m-%dT%H:%M}",
        "akhir": None if last is None else f"{last:%Y-%m-%dT%H:%M}",
        "selisih_jam": None if age is None else round(age, 1),
        "usang": age is None or age > USANG_JAM,
        "baris": rows,
        "pola": pola_jam(local, dataset().loc[dataset().kota.eq(kota)]) if terbaru is None else None})


# ---------- prakiraan ----------
def _outlook_cached(kota, today):
    key = ("cuaca", kota, today)
    cached = _cache_get(key)
    if cached is None:
        cached = ringkasan(outlook(kota), today)
        _cache_put(key, cached, 900)
    return cached


def cuaca(kota, today=None):
    """Isi /api/cuaca. Galat jaringan atau respons tak terpakai menjadi Galat 503."""
    today = today or datetime.now(WIB).date()
    try:
        data = dict(_outlook_cached(kota, today))
    except (OSError, HTTPException, ValueError, KeyError, TypeError):
        raise Galat(503, PESAN_PRAKIRAAN) from None
    data["kota"] = kota
    data["pm25"] = _pm25_terakhir(kota)
    return data


def _pm25_terakhir(kota):
    try:
        local, _ = _riwayat_kota(kota)
    except (OSError, ValueError, KeyError):
        return None
    valid = local.dropna(subset=[PM]).sort_values("waktu")
    if valid.empty:
        return None
    row = valid.iloc[-1]
    return bersih({"nilai": row[PM], "waktu": f"{row.waktu:%Y-%m-%dT%H:%M}"})


# ---------- sensor ----------
def _wib(text):
    return datetime.fromisoformat(text).astimezone(WIB)


def sensor(kota, now=None):
    now = now or datetime.now(WIB)
    pastikan_penyimpanan()
    try:
        with session() as store:
            devices = [name for city, name in store.devices() if city == kota]
            history = {name: store.history(kota, name) for name in devices}
            cloud, table = store.cloud, store.table
    except DB_ERRORS:
        raise Galat(503, "Database sensor tidak terjangkau. Coba lagi sebentar lagi.") from None
    try:
        local, _ = _riwayat_kota(kota)
        model = dict(zip(local.waktu, local[TEMP]))
    except (OSError, ValueError, KeyError):
        model = {}

    measurements, devices_out = {}, []
    for name in devices:
        items = []
        for stamp, temp, rh in history[name]:
            moment = _wib(stamp)
            model_temp = model.get(pd.Timestamp(moment.replace(tzinfo=None, minute=0, second=0, microsecond=0)))
            items.append({"waktu": moment.isoformat(timespec="seconds"), "suhu": temp, "kelembapan": rh,
                          "model_suhu": model_temp,
                          "selisih": None if model_temp is None else temp - model_temp,
                          "_moment": moment})
        last = items[0]["_moment"] if items else None
        hour = sum(1 for item in items if now - item["_moment"] <= timedelta(hours=1))
        devices_out.append({"sensor": name, "terakhir": None if last is None else last.isoformat(timespec="seconds"),
                            "aktif": last is not None and now - last < timedelta(minutes=AKTIF_MENIT),
                            "kiriman_1_jam": hour, "kiriman_1_jam_batas": bool(items) and hour == len(items) == 60,
                            "_last": last})
        measurements[name] = [{k: v for k, v in item.items() if k != "_moment"} for item in items]
    devices_out.sort(key=lambda item: (item["_last"] is None, -(item["_last"].timestamp() if item["_last"] else 0)))
    latest = None
    if devices_out and devices_out[0]["_last"]:
        first = devices_out[0]
        row = measurements[first["sensor"]][0]
        latest = {"sensor": first["sensor"], "aktif": first["aktif"], "kiriman_1_jam": first["kiriman_1_jam"],
                  "kiriman_1_jam_batas": first["kiriman_1_jam_batas"], **row}
    for item in devices_out:
        del item["_last"]
    return bersih({"kota": kota, "sumber": "Supabase" if cloud else "SQLite lokal", "tabel": table,
                   "perangkat": devices_out, "pengukuran": measurements, "terbaru": latest})


# ---------- penerima sensor (POST /pengukuran) ----------
def cek_token(authorization, token):
    if not token:
        raise Galat(503, "SENSOR_TOKEN belum diisi di server penerima.")
    if not hmac.compare_digest((authorization or "").encode(), f"Bearer {token}".encode()):
        raise Galat(401, "Token salah.")


def simpan_pengukuran(body):
    """Aturan sama dengan sensor.py: 400 data salah, 201 baru, 200 ulang, 409 beda, 503 database.
    Token diperiksa lebih dulu lewat cek_token()."""
    try:
        if not 0 < len(body) <= BATAS_BADAN:
            raise ValueError("Ukuran JSON harus 1–4096 byte.")
        row = measurement(json.loads(body))
    except (ValueError, RecursionError) as exc:
        raise Galat(400, str(exc)) from None
    pastikan_penyimpanan()
    try:
        with session() as store:
            status = store.save(row)
    except DB_ERRORS:
        raise Galat(503, "Database tidak terjangkau. Kirim ulang dengan waktu pengukuran yang sama.") from None
    return status
