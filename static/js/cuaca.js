/* Kondisi saat ini, prakiraan per jam, dan prakiraan tujuh hari. */
(function () {
  "use strict";
  const U = window.U, e = U.esc;

  function kerangka() {
    const blok = function (t, r) { return '<div class="skel" style="height:' + t + "px;border-radius:" + (r || 24) + 'px"></div>'; };
    return '<div class="hero-baris"><div class="skel" style="flex:1 1 480px;height:300px;border-radius:30px"></div><div class="stat-petak">' +
      blok(110, 20) + blok(110, 20) + blok(110, 20) + blok(110, 20) + "</div></div>" + blok(190) + blok(150);
  }

  function kondisi(k, ukuran, tebal, warna) {
    return '<span role="img" aria-label="' + e(k.label) + '" title="' + e(k.label) + '" style="display:inline-flex">' + U.ikon(k.ikon, ukuran, tebal, warna) + "</span>";
  }

  function hero(kota, c) {
    const s = c.sekarang;
    return '<section class="hero" aria-label="Cuaca saat ini di ' + e(kota) + '">' +
      '<div class="atas"><span class="kota">' + U.ikon("kota", 18, 1.8, "#fff") + e(kota) + " · saat ini</span><span>" + U.waktu.lengkap(c.waktu) + "</span></div>" +
      '<div class="tengah"><div class="suhu">' + U.angka(s.suhu, 1, "°") + "</div>" + kondisi(s.kondisi, 120, 1.2, "#fff") + "</div>" +
      '<div class="kondisi">' + e(s.kondisi.label) + "</div>" +
      '<div class="rinci">Terasa ' + U.angka(s.terasa, 1, "°") + " · terendah " + U.angka(s.min, 1, "°") + " · tertinggi " + U.angka(s.maks, 1, "°") + "</div></section>";
  }

  function statistik(c) {
    const s = c.sekarang, pm = c.pm25;
    const kartu = function (ik, warna, nilai, label) {
      return '<div class="stat"><span style="color:' + warna + '">' + U.ikon(ik, 26) + '</span><div class="nilai">' + nilai + '</div><div class="label">' + label + "</div></div>";
    };
    return '<div class="stat-petak">' +
      kartu("lembap", "var(--accent)", U.bulat(s.kelembapan, "%"), "Kelembapan") +
      kartu("angin", "var(--accent)", U.angka(s.angin, 1, " km/j"), "Angin") +
      kartu("pm", "var(--pm)", pm ? U.bulat(pm.nilai, " µg/m³") : "—", pm ? "PM2.5 " + U.waktu.tglJam(pm.waktu) + " · estimasi CAMS" : "PM2.5 · estimasi CAMS") +
      kartu("terbit", "var(--warm)", (s.terbit || "—") + " · " + (s.terbenam || "—"), "Terbit · terbenam") + "</div>";
  }

  function tips(c) {
    if (!c.tips_hujan) return "";
    return '<section class="kartu rapat"><div style="display:flex;gap:14px;align-items:center"><span style="color:var(--warm)">' + U.ikon("hujan", 30) + "</span>" +
      '<div style="line-height:1.5"><strong>Hujan paling mungkin pukul ' + e(c.tips_hujan.jam) + '</strong><span style="color:var(--mute)"> · peluang ' +
      U.bulat(c.tips_hujan.peluang, "%") + ". Kalau ada kegiatan luar ruang, siapkan payung.</span></div></div></section>";
  }

  function perJam(c) {
    const item = c.per_jam.map(function (j, i) {
      const tinggi = Math.max(2, Math.round((j.peluang || 0) * 0.34));
      return '<div class="jam' + (i === 0 ? " kini" : "") + '"><div class="w">' + e(j.jam) + '</div><div class="ik">' + kondisi(j.kondisi, 30) + "</div>" +
        '<div class="t">' + U.bulat(j.suhu, "°") + '</div><div class="batang"><i style="height:' + tinggi + 'px"></i></div><div class="p">' +
        (j.peluang == null ? "—" : U.bulat(j.peluang, "%")) + '<span class="sr-only"> peluang hujan</span></div></div>';
    }).join("");
    return '<section class="kartu"><div class="kepala"><h2>Per jam</h2><span class="kecil">24 jam ke depan, waktu WIB · batang dan persen menunjukkan peluang hujan</span></div>' +
      '<div class="jam-baris" tabindex="0" role="region" aria-label="Prakiraan per jam, geser untuk melihat lebih banyak">' + item + "</div></section>";
  }

  function tujuhHari(c) {
    const semua = c.tujuh_hari.filter(function (d) { return d.min != null && d.maks != null; });
    const rendah = Math.min.apply(null, semua.map(function (d) { return d.min; }));
    const tinggi = Math.max.apply(null, semua.map(function (d) { return d.maks; }));
    const rentang = tinggi - rendah || 1;
    const baris = c.tujuh_hari.map(function (d) {
      const ada = d.min != null && d.maks != null;
      const kiri = ada ? ((d.min - rendah) / rentang) * 100 : 0, lebar = ada ? Math.max(4, ((d.maks - d.min) / rentang) * 100) : 0;
      return '<div class="hari"><span class="nm">' + e(d.hari.slice(0, 3)) + '</span><span class="tg">' + e(d.tgl) + "</span>" + kondisi(d.kondisi, 24) +
        '<span class="kd">' + e(d.kondisi.label) + '</span><span class="pl">' + (d.peluang == null ? "—" : U.bulat(d.peluang, "%")) + '</span>' +
        '<span class="mn">' + U.bulat(d.min, "°") + '</span><div class="rg" title="Rerata ' + U.angka(d.rerata, 1, "°") + '"><i style="left:' + kiri + "%;width:" + lebar + '%"></i></div>' +
        '<span class="mx">' + U.bulat(d.maks, "°") + '</span><span class="mm">' + U.angka(d.presipitasi, 1, " mm") + '</span><span class="an">' + U.angka(d.angin_maks, 1, " km/j") + "</span></div>";
    }).join("");
    return '<section class="kartu" style="flex:3 1 560px"><div class="kepala"><h2>7 hari ke depan</h2><span class="kecil">peluang hujan · min–maks · presipitasi · angin maksimum</span></div><div class="gulir">' + baris + "</div></section>";
  }

  function tabelRiwayat(r) {
    const baris = r.baris.slice().reverse().map(function (b) {
      return "<tr><td>" + U.waktu.tglJam(b.waktu) + "</td><td>" + U.angka(b.temperature_2m, 1) + "</td><td>" + U.bulat(b.relative_humidity_2m) + "</td><td>" +
        U.angka(b.precipitation, 1) + "</td><td>" + U.angka(b.wind_speed_10m, 1) + "</td><td>" + U.bulat(b.pm2_5) + "</td></tr>";
    }).join("");
    return '<section class="kartu"><div class="kepala"><h2>Riwayat per jam terbaru</h2><span class="kecil">' + e(r.sumber_data) + " · " + U.ribuan(r.jumlah) + ' jam · <a href="/riwayat?kota=' + encodeURIComponent(r.kota) + '">Lihat semua</a></span></div>' +
      '<div class="gulir"><table><thead><tr><th>Waktu (WIB)</th><th>Suhu (°C)</th><th>Kelembapan (%)</th><th>Presipitasi (mm)</th><th>Angin (km/j)</th><th>PM2.5 (µg/m³)</th></tr></thead><tbody>' + baris + "</tbody></table></div></section>";
  }

  async function gagalPrakiraan(kota, ctx, galat) {
    const pesan = galat.status === 503 || galat.status === 0 ? galat.message : "Prakiraan Open-Meteo sedang tidak tersedia. Riwayat per jam tersedia di bawah.";
    ctx.isi.innerHTML = U.catatan(pesan, "hangat", U.tombolUlang()) + '<div class="skel" style="height:240px;border-radius:24px"></div>';
    document.getElementById("coba-lagi").addEventListener("click", function () { window.Shell.ulang(); });
    let bawah;
    try {
      bawah = tabelRiwayat(await U.api("/api/riwayat", { kota: kota, terbaru: 12 }));
    } catch (err) {
      bawah = '<section class="kartu">' + U.catatan("Riwayat per jam juga belum bisa dimuat: " + err.message, "hangat") + "</section>";
    }
    if (ctx.berlaku()) ctx.isi.lastElementChild.outerHTML = bawah;
  }

  async function muat(kota, ctx) {
    let c;
    try {
      c = await U.api("/api/cuaca", { kota });
    } catch (err) {
      if (!ctx.berlaku() || ctx.senyap) return;
      return gagalPrakiraan(kota, ctx, err);
    }
    if (!ctx.berlaku()) return;
    ctx.isi.innerHTML = '<div class="hero-baris">' + hero(kota, c) + statistik(c) + "</div>" + tips(c) + perJam(c) +
      tujuhHari(c);
  }

  window.Shell.mulai({ kunci: "cuaca", judul: "Cuaca hari ini", sub: "Prakiraan Open-Meteo · diperbarui paling sering tiap 15 menit", kerangka: kerangka, muat: muat, segarkan: 60000 });
})();
