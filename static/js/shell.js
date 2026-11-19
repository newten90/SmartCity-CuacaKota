/* Kerangka halaman: rail navigasi (desktop) / tab bar (HP), bar atas dengan pilihan kota, dan atribusi.
   Kota terpilih disimpan di ?kota= dan localStorage sehingga sama di semua halaman. */
(function () {
  "use strict";
  const U = window.U;
  const KOTA = ["Bandung", "Jakarta", "Surabaya"];
  const MENU = [["/", "cuaca", "Cuaca"], ["/analisis", "analisis", "Analisis"], ["/riwayat", "riwayat", "Riwayat"],
    ["/sensor", "sensor", "Sensor"], ["/kota", "kota", "Kota"]];
  const ATRIBUSI = 'Prakiraan: <a href="https://open-meteo.com/en/docs">Open-Meteo Forecast API</a>. Arsip: ECMWF ERA5 via Open-Meteo. ' +
    'PM2.5: estimasi model Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo, satu titik model per kota, bukan sensor. ' +
    '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.';

  function simpan(nama, nilai) { try { localStorage.setItem(nama, nilai); } catch (e) { /* mode privat */ } }
  function baca(nama) { try { return localStorage.getItem(nama); } catch (e) { return null; } }

  function kotaAwal() {
    const dariUrl = new URLSearchParams(location.search).get("kota");
    if (KOTA.indexOf(dariUrl) >= 0) return dariUrl;
    const tersimpan = baca("kota");
    return KOTA.indexOf(tersimpan) >= 0 ? tersimpan : KOTA[0];
  }

  function mulai(cfg) {
    let kota = kotaAwal();
    simpan("kota", kota);
    let versi = 0;
    document.title = cfg.judul + " · Cuaca Kota";
    const app = document.getElementById("app");
    app.className = "rangka";
    app.innerHTML =
      '<nav class="rail" aria-label="Halaman"><div class="logo">' + U.ikon("cerah-berawan", 28, 1.8, "#fff") + "</div>" +
      MENU.map(function (m) {
        return '<a class="nav-item" href="' + m[0] + '" data-nav="' + m[1] + '"' + (m[1] === cfg.kunci ? ' aria-current="page"' : "") + ">" +
          U.ikon(m[1] === "cuaca" ? "cuaca" : m[1], 24) + m[2] + "</a>";
      }).join("") + "</nav>" +
      '<main class="isi"><div class="bar"><div><h1>' + U.esc(cfg.judul) + '</h1><div class="sub" id="sub">' + U.esc(cfg.sub || "") + "</div></div>" +
      '<div class="kelompok" role="group" aria-label="Pilih kota">' +
      KOTA.map(function (k) { return '<button type="button" class="tombol-kota" data-kota="' + k + '" aria-pressed="false">' + U.ikon("kota", 16) + k + "</button>"; }).join("") +
      '</div></div><div id="halaman" aria-live="polite"></div><footer class="atribusi">' + ATRIBUSI + "</footer></main>";

    const isi = document.getElementById("halaman");
    const ctx = function (senyap) {
      const saya = ++versi;
      return { isi: isi, kota: kota, senyap: !!senyap, berlaku: function () { return saya === versi; } };
    };

    function segarkanKendali() {
      document.querySelectorAll(".tombol-kota").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.kota === kota)); });
      document.querySelectorAll(".nav-item").forEach(function (a) {
        const m = MENU.find(function (x) { return x[1] === a.dataset.nav; });
        a.setAttribute("href", m[0] + "?kota=" + encodeURIComponent(kota));
      });
      const url = new URL(location.href);
      url.searchParams.set("kota", kota);
      history.replaceState(null, "", url);
    }

    function jalankan(senyap) {
      const c = ctx(senyap);
      if (!senyap) isi.innerHTML = cfg.kerangka ? cfg.kerangka(kota) : "";
      Promise.resolve(cfg.muat(kota, c)).catch(function (e) {
        if (c.berlaku()) isi.innerHTML = U.catatan(e && e.message ? e.message : "Terjadi kesalahan tak terduga.", "hangat");
      });
    }

    document.querySelector(".kelompok").addEventListener("click", function (e) {
      const b = e.target.closest("[data-kota]");
      if (!b || b.dataset.kota === kota) return;
      kota = b.dataset.kota;
      simpan("kota", kota);
      segarkanKendali();
      if (cfg.gantiKota) cfg.gantiKota(kota);
      jalankan(false);
    });

    window.Shell.ulang = function () { jalankan(false); };
    window.Shell.sub = function (teks) { document.getElementById("sub").textContent = teks; };
    window.Shell.kota = function () { return kota; };
    segarkanKendali();
    jalankan(false);
    if (cfg.segarkan) {
      setInterval(function () { if (!document.hidden) jalankan(true); }, cfg.segarkan);
    }
  }

  window.Shell = { mulai: mulai, KOTA: KOTA };
})();
