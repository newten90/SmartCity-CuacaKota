/* Halaman Riwayat per jam: sumber data, waktu sinkron terakhir, grafik, dan tabel dari /api/riwayat. */
(function () {
  "use strict";
  const U = window.U, e = U.esc, W = U.WARNA;
  const VARIABEL = [
    { nama: "Suhu", kolom: "temperature_2m", satuan: "°C", warna: W.aksen, digit: 1 },
    { nama: "Kelembapan", kolom: "relative_humidity_2m", satuan: "%", warna: W.aksen, digit: 0 },
    { nama: "Presipitasi", kolom: "precipitation", satuan: "mm", warna: W.aksen, digit: 1, batang: true },
    { nama: "Angin", kolom: "wind_speed_10m", satuan: "km/j", warna: W.aksen, digit: 1 },
    { nama: "PM2.5", kolom: "pm2_5", satuan: "µg/m³", warna: W.pm, digit: 1 },
  ];
  const HALAMAN = 100;
  let pilihan = 0, tampil = HALAMAN, data = null;

  function kerangka() {
    const b = function (t) { return '<div class="skel" style="height:' + t + 'px;border-radius:24px"></div>'; };
    return b(90) + b(330) + b(300);
  }

  function umur(jam) {
    if (jam == null) return "";
    if (jam < 1) return "kurang dari 1 jam lalu";
    if (jam < 48) return U.angka(Math.floor(jam), 0) + " jam lalu";
    return U.angka(Math.floor(jam / 24), 0) + " hari lalu";
  }

  function sumberKartu(d) {
    const cloud = d.sumber_data === "Supabase";
    return '<section class="kartu rapat"><div style="display:flex;flex-wrap:wrap;gap:18px;align-items:center;justify-content:space-between">' +
      '<div style="display:flex;gap:12px;align-items:center"><span style="color:var(--accent)">' + U.ikon("basisdata", 28) + "</span><div>" +
      '<div style="font-weight:800;font-size:16px">' + (cloud ? "Supabase · " + e(d.tabel) : "Salinan impor di repositori · " + e(d.tabel)) + "</div>" +
      '<div class="kecil">' + U.ribuan(d.jumlah) + " jam · " + U.waktu.tanggalPendek(d.awal) + " – " + U.waktu.tanggalPendek(d.akhir) + " " + U.waktu.jam(d.akhir) + " WIB</div>" +
      '<div class="kecil" style="margin-top:4px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">Sinkron terakhir: ' + (d.akhir ? U.waktu.lengkap(d.akhir) + " · " + umur(d.selisih_jam) : "belum ada data") +
      (d.usang ? ' <span class="lencana hangat">Lebih dari 6 jam</span>' : ' <span class="lencana ok">Terbaru</span>') + "</div></div></div>" +
      '<a class="btn gelap" href="/api/riwayat.csv?kota=' + encodeURIComponent(d.kota) + '" download>' + U.ikon("unduh", 18) + "Unduh riwayat per jam</a></div></section>";
  }

  function peringatan(d) {
    let isi = "";
    if (d.catatan) isi += U.catatan(d.catatan);
    if (d.usang && d.jumlah) {
      isi += U.catatan("Data terakhir sudah lebih dari 6 jam. Sinkron otomatis mungkin tertunda atau gagal; periksa workflow GitHub Actions dan koneksi Supabase.", "hangat");
    }
    return isi;
  }

  function grafikKartu() {
    return '<section class="kartu"><div class="kepala"><h2>Grafik per jam</h2><div class="kelompok" role="group" aria-label="Pilih variabel">' +
      VARIABEL.map(function (v, i) { return '<button type="button" class="chip" data-var="' + i + '" aria-pressed="' + (i === pilihan) + '">' + v.nama + "</button>"; }).join("") +
      '</div></div><div id="g-riwayat" class="grafik tinggi"></div>' +
      '<p class="kecil" style="margin-top:6px">Area biru muda dan garis putus-putus menandai jam yang memakai model operasional, karena data ERA5 baru tersedia beberapa hari kemudian. PM2.5 dari CAMS via Open-Meteo.</p></section>';
  }

  function gambarGrafik() {
    const v = VARIABEL[pilihan], baris = data.baris, el = document.getElementById("g-riwayat");
    const op = baris.map(function (b) { return /Best Match/i.test(b.sumber || ""); });
    const x = baris.map(function (b) { return b.waktu; });
    const y = baris.map(function (b) { return b[v.kolom]; });
    const arsip = y.map(function (n, i) { return op[i] ? null : n; });
    const model = y.map(function (n, i) { return op[i] || op[i + 1] ? n : null; });
    const garis = function (nilai, putus) {
      return { type: "scatter", mode: "lines", x: x, y: nilai, connectgaps: false, line: { color: v.warna, width: 2.2, dash: putus ? "dash" : "solid" },
        hovertemplate: "%{x|%d/%m %H:%M}: %{y:." + v.digit + "f} " + v.satuan + "<extra></extra>" };
    };
    const jejak = v.batang ? [{ type: "bar", x: x, y: y, marker: { color: v.warna }, hovertemplate: "%{x|%d/%m %H:%M}: %{y:." + v.digit + "f} " + v.satuan + "<extra></extra>" }]
      : [garis(arsip, false), garis(model, true)];
    const bentuk = [], catatan = [];
    for (let i = 0; i < op.length; i++) {
      if (!op[i]) continue;
      let j = i;
      while (j + 1 < op.length && op[j + 1]) j++;
      bentuk.push({ type: "rect", xref: "x", yref: "paper", x0: x[i], x1: x[j], y0: 0, y1: 1, fillcolor: W.lunak, line: { width: 0 }, layer: "below" });
      catatan.push({ x: x[i], xref: "x", y: 1, yref: "paper", text: "model operasional", showarrow: false, xanchor: "left", yanchor: "top", xshift: 6,
        font: { color: W.aksen, size: 12 } });
      i = j;
    }
    if (op.some(function (n) { return !n; })) {
      catatan.push({ x: x[0], xref: "x", y: 1, yref: "paper", text: "arsip ERA5", showarrow: false, xanchor: "left", yanchor: "top", xshift: 6, font: { color: W.teks, size: 12 } });
    }
    U.gambar(el, jejak, U.tata({ height: 300, shapes: bentuk, annotations: catatan, xaxis: { type: "date", gridcolor: W.garis, zeroline: false, fixedrange: true, tickformat: "%d %b" },
      yaxis: { gridcolor: W.garis, zeroline: false, fixedrange: true, automargin: true, title: { text: v.nama + " (" + v.satuan + ")", font: { size: 12 } } } }),
      v.nama + " per jam " + data.kota + " sejak " + U.waktu.tanggalPendek(data.awal));
  }

  function tabel() {
    const urut = data.baris.slice().reverse(), tampilkan = urut.slice(0, tampil);
    const baris = tampilkan.map(function (b) {
      const model = /Best Match/i.test(b.sumber || "");
      return "<tr><td>" + U.waktu.tglJam(b.waktu) + "</td><td>" + U.angka(b.temperature_2m, 1) + "</td><td>" + U.bulat(b.relative_humidity_2m) + "</td><td>" + U.angka(b.precipitation, 1) +
        "</td><td>" + U.angka(b.wind_speed_10m, 1) + "</td><td>" + (b.weather_code == null ? "—" : Math.round(b.weather_code)) + "</td><td>" + U.bulat(b.pm2_5) +
        '</td><td><span class="lencana" style="' + (model ? "" : "background:var(--bg);color:var(--mute)") + '">' + e(String(b.sumber || "—").replace("Open-Meteo ", "")) + "</span></td></tr>";
    }).join("");
    const sisa = urut.length - tampilkan.length;
    return '<section class="kartu"><div class="kepala"><h2>Tabel per jam</h2><span class="kecil">terbaru di atas · menampilkan ' + U.ribuan(tampilkan.length) + " dari " + U.ribuan(urut.length) + " jam</span></div>" +
      '<div class="gulir"><table style="min-width:820px"><thead><tr><th>Waktu (WIB)</th><th>Suhu (°C)</th><th>Kelembapan (%)</th><th>Presipitasi (mm)</th><th>Angin (km/j)</th><th>Kode WMO</th><th>PM2.5 (µg/m³)</th><th>Sumber</th></tr></thead><tbody>' + baris + "</tbody></table></div>" +
      (sisa > 0 ? '<div style="margin-top:12px"><button type="button" class="btn" id="lagi">Tampilkan ' + Math.min(HALAMAN, sisa) + " jam lagi</button></div>" : "") + "</section>";
  }

  function pasang() {
    document.querySelectorAll("[data-var]").forEach(function (b) {
      b.addEventListener("click", function () {
        pilihan = Number(b.dataset.var);
        document.querySelectorAll("[data-var]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        gambarGrafik();
      });
    });
    const lagi = document.getElementById("lagi");
    if (lagi) lagi.addEventListener("click", function () { tampil += HALAMAN; document.getElementById("tabel").innerHTML = tabel(); pasang(); });
  }

  async function muat(kota, ctx) {
    let d;
    try {
      d = await U.api("/api/riwayat", { kota: kota });
    } catch (err) {
      if (!ctx.berlaku()) return;
      ctx.isi.innerHTML = U.catatan(err.message, "hangat", U.tombolUlang());
      document.getElementById("coba-lagi").addEventListener("click", function () { window.Shell.ulang(); });
      return;
    }
    if (!ctx.berlaku()) return;
    data = d; tampil = HALAMAN;
    window.Shell.sub("Sejak 1 Oktober 2026 · data grid meteorologi, bukan pengukuran perangkat");
    if (!d.jumlah) {
      ctx.isi.innerHTML = sumberKartu(d) + peringatan(d) + '<section class="kartu"><div class="kosong">' + U.ikon("riwayat", 34) + '<div class="judul">Belum ada riwayat</div><div class="isi-kosong">Jalankan sinkron_riwayat.py untuk mengisi riwayat per jam.</div></div></section>';
      return;
    }
    ctx.isi.innerHTML = sumberKartu(d) + peringatan(d) + grafikKartu() + '<div id="tabel">' + tabel() + "</div>";
    pasang();
    gambarGrafik();
  }

  window.Shell.mulai({ kunci: "riwayat", judul: "Riwayat per jam", sub: "Sejak 1 Oktober 2026", kerangka: kerangka, muat: muat });
})();
