"""Aplikasi web Cuaca Kota: JSON API dan halaman statis. Jalankan:
    .\\.venv\\Scripts\\python -m uvicorn main:app --reload
Di Vercel berkas ini dikenali otomatis sebagai entrypoint FastAPI (instance bernama app)."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from lingkungan import muat_env

muat_env()

import layanan  # noqa: E402  (setelah muat_env supaya .env ikut terbaca)
from ambil_data import CITIES  # noqa: E402
from layanan import Galat  # noqa: E402
from jsonaman import bersih  # noqa: E402

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
app = FastAPI(title="Cuaca Kota", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

CACHE_PRAKIRAAN = "public, max-age=60, s-maxage=900, stale-while-revalidate=60"
CACHE_RIWAYAT = "public, max-age=60, s-maxage=900, stale-while-revalidate=60"
CACHE_CADANGAN = "public, max-age=30, s-maxage=60"
CACHE_ARSIP = "public, max-age=300, s-maxage=86400"
TANPA_CACHE = "no-store"


def kirim(data, cache=TANPA_CACHE, status=200):
    return JSONResponse(bersih(data), status_code=status, headers={"Cache-Control": cache})


def unduh(teks, nama):
    return Response(teks, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nama}"', "Cache-Control": TANPA_CACHE})


@app.exception_handler(Galat)
async def galat_handler(request: Request, exc: Galat):
    return kirim({"pesan": exc.pesan}, status=exc.status)


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    pesan = {404: "Alamat tidak ditemukan.", 405: "Metode tidak diizinkan untuk alamat ini."}.get(exc.status_code, str(exc.detail))
    return kirim({"pesan": pesan}, status=exc.status_code)


# ---------- API ----------
@app.get("/api/kota")
def api_kota():
    return kirim([{"nama": name, "lat": lat, "lon": lon} for name, (lat, lon) in CITIES.items()], CACHE_ARSIP)


@app.get("/api/cuaca")
def api_cuaca(kota: str | None = None):
    return kirim(layanan.cuaca(layanan.cek_kota(kota)), CACHE_PRAKIRAAN)


@app.get("/api/riwayat")
def api_riwayat(kota: str | None = None, terbaru: int | None = None):
    kota = layanan.cek_kota(kota)
    if terbaru is not None and not 1 <= terbaru <= 10000:
        raise Galat(400, "Parameter terbaru harus berupa bilangan 1–10000.")
    data = layanan.riwayat(kota, terbaru=terbaru)
    return kirim(data, CACHE_RIWAYAT if data["sumber_data"] == "Supabase" else CACHE_CADANGAN)


@app.get("/api/riwayat.csv")
def api_riwayat_csv(kota: str | None = None):
    return unduh(*layanan.riwayat_csv(layanan.cek_kota(kota)))


@app.get("/api/analisis")
def api_analisis(kota: str | None = None, dari: str | None = None, sampai: str | None = None):
    kota = layanan.cek_kota(kota)
    dari, sampai = layanan.cek_rentang(dari, sampai)
    return kirim(layanan.analisis(kota, dari, sampai), CACHE_ARSIP)


@app.get("/api/analisis.csv")
def api_analisis_csv(kota: str | None = None, dari: str | None = None, sampai: str | None = None):
    kota = layanan.cek_kota(kota)
    dari, sampai = layanan.cek_rentang(dari, sampai)
    return unduh(*layanan.analisis_csv(kota, dari, sampai))


# ---------- halaman ----------
def halaman(nama):
    def tampil():
        return FileResponse(STATIC / f"{nama}.html", headers={"Cache-Control": "public, max-age=0, must-revalidate"})
    return tampil


for path, nama in [("/", "cuaca"), ("/analisis", "analisis"), ("/riwayat", "riwayat"),
                   ("/kota", "kota")]:
    app.add_api_route(path, halaman(nama), methods=["GET"], include_in_schema=False)
