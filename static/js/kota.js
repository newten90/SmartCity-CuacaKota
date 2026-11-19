/* Halaman Pilih kota: suhu sekarang, kondisi, serta rerata suhu dan hujan 2025 per kota. Klik kartu = pilih kota lalu ke Cuaca. */
(function () {
  "use strict";
  const U = window.U, e = U.esc, KOTA = window.Shell.KOTA;

  function kerangka() {
    return '<div class="baris">' + KOTA.map(function () { return '<div class="skel" style="flex:1 1 360px;height:420px;border-radius:28px"></div>'; }).join("") + "</div>";
  }

  function kartu(nama, aktif, cuaca, tahunan) {
    const c = cuaca.status === "fulfilled" ? cuaca.value : null, s = c && c.sekarang;
    const hitung = tahunan && tahunan.tabel_kota.find(function (r) { return r.kota === nama; });
    return '<a class="kota-kartu' + (aktif ? " dipilih" : "") + '" href="/?kota=' + encodeURIComponent(nama) + '" data-pilih="' + e(nama) + '" aria-label="' + (aktif ? "Kota terpilih: " : "Pilih kota ") + e(nama) + '">' +
      '<div class="baris2"><span class="nm">' + e(nama) + '</span><span class="lencana">' + (aktif ? "Dipilih" : "Pilih") + "</span></div>" +
      '<div class="baris2"><span class="suhu">' + (s ? U.angka(s.suhu, 1, "°") : "—") + "</span>" + (s ? U.ikon(s.kondisi.ikon, 72, 1.4) : "") + "</div>" +
      '<div style="font-size:16px;font-weight:700">' + (s ? e(s.kondisi.label) : "Prakiraan tidak tersedia") + "</div>" +
      '<div class="kecil">' + (s ? "Terasa " + U.angka(s.terasa, 1, "°") + " · " + U.angka(s.min, 1, "°") + " / " + U.angka(s.maks, 1, "°") + " · kelembapan " + U.bulat(s.kelembapan, "%") : "Open-Meteo belum bisa dihubungi untuk kota ini.") + "</div>" +
      '<div class="dua"><div><span class="kecil">Rerata suhu 2025</span><b>' + (hitung ? U.angka(hitung.temperature_2m, 2, " °C") : "—") + '</b></div><div><span class="kecil">Hujan 2025</span><b>' + (hitung ? U.angka(hitung.rain, 1, " mm") : "—") + "</b></div></div></a>";
  }

  async function muat(kota, ctx) {
    const hasil = await Promise.all([
      Promise.allSettled(KOTA.map(function (k) { return U.api("/api/cuaca", { kota: k }); })),
      U.api("/api/analisis", { kota: kota }).catch(function () { return null; }),
      U.api("/api/kota").catch(function () { return []; }),
    ]);
    if (!ctx.berlaku()) return;
    const koordinat = hasil[2].map(function (k) { return e(k.nama) + " (" + U.angka(k.lat, 4) + "; " + U.angka(k.lon, 4) + ")"; }).join(", ");
    ctx.isi.innerHTML = '<div class="baris">' + KOTA.map(function (k, i) { return kartu(k, k === kota, hasil[0][i], hasil[1]); }).join("") + "</div>" +
      '<section class="kartu rapat"><div style="display:flex;gap:12px;align-items:flex-start;font-size:14px;line-height:1.55;color:var(--mute)"><span style="color:var(--accent)">' + U.ikon("info", 22) + "</span><span>Setiap kota diwakili satu titik koordinat di <code>ambil_data.py</code>" +
      (koordinat ? ": " + koordinat : "") + ". Menambah kota berarti menambah koordinat lalu mengambil ulang arsip dan riwayat.</span></div></section>";
    ctx.isi.querySelectorAll("[data-pilih]").forEach(function (a) {
      a.addEventListener("click", function () { try { localStorage.setItem("kota", a.dataset.pilih); } catch (err) { /* mode privat */ } });
    });
  }

  window.Shell.mulai({ kunci: "kota", judul: "Pilih kota", sub: "Bandung sebagai fokus, Jakarta dan Surabaya sebagai pembanding", kerangka: kerangka, muat: muat });
})();
