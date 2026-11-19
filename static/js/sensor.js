/* Halaman Sensor IoT: pembacaan terakhir, perbandingan dengan model, tren, perangkat, dan tabel kiriman dari /api/sensor. */
(function () {
  "use strict";
  const U = window.U, e = U.esc, W = U.WARNA;
  const KODE = [["201", "pengukuran baru tersimpan", "var(--ok-fg)"], ["200", "kiriman ulang yang sama", "var(--accent)"], ["400", "data di luar rentang", "var(--warm)"],
    ["401", "token salah", "var(--warm)"], ["409", "nilai berbeda di waktu sama", "var(--warm)"], ["503", "database tidak terjangkau", "var(--warm)"]];
  let dipilih = null, kotaSebelumnya = null, d = null;

  function kerangka() {
    const b = function (t) { return '<div class="skel" style="height:' + t + 'px;border-radius:24px"></div>'; };
    return b(240) + '<div class="baris">' + b(260) + b(260) + "</div>" + b(240);
  }

  function status(p) {
    return '<div class="status' + (p.aktif ? "" : " mati") + '"><span class="titik"></span>' +
      (p.aktif ? "Aktif · kiriman terakhir " + U.waktu.jam(p.terakhir) + " WIB" : "Tidak aktif · kiriman terakhir " + U.waktu.tglJam(p.terakhir) + " WIB") + "</div>";
  }

  function cincin(persen) {
    const ada = persen != null, keliling = 2 * Math.PI * 62, garis = ada ? Math.max(0, Math.min(100, persen)) / 100 * keliling : 0;
    return '<svg width="190" height="190" viewBox="0 0 150 150" role="img" aria-label="Kelembapan sensor ' + (ada ? Math.round(persen) + " persen" : "tidak tersedia") + '" style="max-width:100%">' +
      '<circle cx="75" cy="75" r="62" fill="none" stroke="' + W.garis + '" stroke-width="12"/>' +
      '<circle cx="75" cy="75" r="62" fill="none" stroke="' + W.aksen + '" stroke-width="12" stroke-linecap="round" stroke-dasharray="' + garis.toFixed(1) + ' 400" transform="rotate(-90 75 75)"/>' +
      '<text x="75" y="80" text-anchor="middle" font-size="30" font-weight="800" fill="#0F1B2D" font-family="Manrope">' + (ada ? U.bulat(persen, "%") : "—") + "</text>" +
      '<text x="75" y="102" text-anchor="middle" font-size="12" fill="#4A586B" font-family="Manrope">kelembapan</text></svg>';
  }

  function selisih(nilai) {
    if (nilai == null) return "—";
    return (nilai < 0 ? "−" : "+") + U.angka(Math.abs(nilai), 1) + " °C";
  }

  function hero(p, baris) {
    return '<section class="kartu"><div class="sensor-hero"><div><div style="font-size:15px;color:var(--mute);font-weight:600">' + e(p.sensor) + " · " + e(d.kota) + "</div>" + status(p) +
      '<div class="suhu">' + U.angka(baris.suhu, 1, "°") + "</div></div>" + cincin(baris.kelembapan) +
      '<div class="banding"><div><span>Model Open-Meteo, jam sama</span><strong>' + (baris.model_suhu == null ? "—" : U.angka(baris.model_suhu, 1, " °C")) + "</strong></div>" +
      '<div><span>Selisih sensor − model</span><strong style="color:var(--warm)">' + selisih(baris.selisih) + "</strong></div>" +
      '<div><span>Kiriman 1 jam terakhir</span><strong>' + (p.kiriman_1_jam_batas ? "60+" : p.kiriman_1_jam) + "</strong></div></div></div></section>";
  }

  function tren(nama) {
    return '<section class="kartu" style="flex:2 1 460px"><div class="kepala"><h2>Tren ' + d.pengukuran[nama].length + ' pembacaan terakhir</h2></div><div id="g-tren" class="grafik"></div>' +
      '<div style="display:flex;gap:18px;font-size:13px"><span style="color:var(--warm);font-weight:700">— Suhu (°C)</span><span style="color:var(--accent);font-weight:700">— Kelembapan (%)</span></div></section>';
  }

  function perangkat() {
    const baris = d.perangkat.map(function (p) {
      return '<button type="button" class="perangkat" data-sensor="' + e(p.sensor) + '" aria-pressed="' + (p.sensor === dipilih) + '" style="width:100%;background:' + (p.sensor === dipilih ? "var(--row-hi)" : "transparent") +
        ';border:0;border-top:1px solid var(--line);text-align:left;font:inherit;color:inherit;min-height:56px;cursor:pointer"><div><div style="font-weight:800">' + e(p.sensor) + '</div><div class="kecil">' + e(d.kota) + " · " + p.kiriman_1_jam +
        ' kiriman dalam 1 jam</div></div><span class="lencana ' + (p.aktif ? "ok" : "hangat") + '">' + (p.aktif ? "Aktif" : "Tidak aktif") + "</span></button>";
    }).join("");
    return '<section class="kartu" style="flex:1 1 320px"><div class="kepala"><h2>Perangkat</h2></div>' + baris + "</section>";
  }

  function tabel(nama) {
    const baris = d.pengukuran[nama].map(function (b) {
      return "<tr><td>" + U.waktu.tglJam(b.waktu) + "</td><td>" + e(nama) + '</td><td class="tebal">' + U.angka(b.suhu, 1, "°") + "</td><td>" + U.bulat(b.kelembapan, "%") + '</td><td><span class="lencana ok">Tersimpan</span></td></tr>';
    }).join("");
    return '<section class="kartu" style="flex:2 1 560px"><div class="kepala"><h2>Kiriman terakhir · tabel ' + e(d.tabel) + '</h2></div><div class="gulir"><table style="min-width:600px"><thead><tr><th>Waktu (WIB)</th><th>Sensor</th><th>Suhu</th><th>Kelembapan</th><th>Status</th></tr></thead><tbody>' + baris + "</tbody></table></div></section>";
  }

  function arti() {
    return '<section class="kartu" style="flex:1 1 300px"><div class="kepala"><h2>Arti kode balasan</h2></div>' +
      KODE.map(function (k) { return '<div class="kode"><strong style="color:' + k[2] + '">' + k[0] + "</strong><span>" + k[1] + "</span></div>"; }).join("") + "</section>";
  }

  function gambarTren(nama) {
    const urut = d.pengukuran[nama].slice().reverse();
    const x = urut.map(function (b) { return b.waktu.slice(0, 19).replace("T", " "); });
    U.gambar(document.getElementById("g-tren"), [
      { type: "scatter", mode: "lines+markers", marker: { size: 6 }, x: x, y: urut.map(function (b) { return b.suhu; }), line: { color: W.hangat, width: 2.5 }, name: "Suhu", hovertemplate: "%{y:.1f} °C<extra>Suhu</extra>" },
      { type: "scatter", mode: "lines+markers", marker: { size: 6 }, x: x, y: urut.map(function (b) { return b.kelembapan; }), yaxis: "y2", line: { color: W.hujan, width: 2.5 }, name: "Kelembapan", hovertemplate: "%{y:.0f}%<extra>Kelembapan</extra>" },
    ], U.tata({ height: 230, margin: { t: 10, r: 52, b: 34, l: 48 }, xaxis: { type: "date", gridcolor: W.garis, zeroline: false, fixedrange: true, tickformat: "%H:%M" },
      yaxis: { gridcolor: W.garis, zeroline: false, fixedrange: true, automargin: true, title: { text: "Suhu (°C)", font: { size: 12 } } },
      yaxis2: { overlaying: "y", side: "right", showgrid: false, zeroline: false, fixedrange: true, automargin: true, title: { text: "Kelembapan (%)", font: { size: 12 } } } }),
      "Tren suhu dan kelembapan sensor " + nama + " (" + d.kota + ")");
  }

  function pasang(ctx) {
    document.querySelectorAll("[data-sensor]").forEach(function (b) {
      b.addEventListener("click", function () { dipilih = b.dataset.sensor; tampilkan(ctx); });
    });
  }

  function tampilkan(ctx) {
    window.Shell.sub("Data dari penerima HTTP · tersimpan di " + (d.sumber === "Supabase" ? "Supabase" : "SQLite lokal"));
    if (!d.perangkat.length) {
      ctx.isi.innerHTML = '<section class="kartu"><div class="kosong">' + U.ikon("sensor", 38, 1.8, "var(--pm)") + '<div class="judul">Belum ada pengukuran</div>' +
        '<div class="isi-kosong">Jalankan sensor.py lalu kirim POST ke /pengukuran. Di situs yang sudah di-deploy, kirim langsung ke alamat /pengukuran situs ini.</div></div></section>' +
        '<div class="baris">' + arti() + "</div>";
      return;
    }
    if (!d.perangkat.some(function (p) { return p.sensor === dipilih; })) dipilih = d.perangkat[0].sensor;
    const p = d.perangkat.find(function (x) { return x.sensor === dipilih; });
    ctx.isi.innerHTML = hero(p, d.pengukuran[dipilih][0]) + '<div class="baris" style="align-items:flex-start">' + tren(dipilih) + perangkat() + "</div>" +
      '<div class="baris" style="align-items:flex-start">' + tabel(dipilih) + arti() + "</div>";
    pasang(ctx);
    gambarTren(dipilih);
  }

  async function muat(kota, ctx) {
    if (kota !== kotaSebelumnya) { dipilih = null; kotaSebelumnya = kota; }
    try {
      const hasil = await U.api("/api/sensor", { kota: kota });
      if (!ctx.berlaku()) return;
      d = hasil;
      tampilkan(ctx);
    } catch (err) {
      if (!ctx.berlaku() || ctx.senyap) return;
      ctx.isi.innerHTML = U.catatan(err.message, "hangat", U.tombolUlang()) + '<div class="baris">' + arti() + "</div>";
      document.getElementById("coba-lagi").addEventListener("click", function () { window.Shell.ulang(); });
    }
  }

  window.Shell.mulai({ kunci: "sensor", judul: "Sensor IoT", sub: "Data dari penerima HTTP", kerangka: kerangka, muat: muat, segarkan: 60000 });
})();
