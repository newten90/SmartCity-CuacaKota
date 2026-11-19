/* Halaman Analisis 2025: ringkasan, grafik, tabel tiga kota, dan korelasi dari /api/analisis. */
(function () {
  "use strict";
  const U = window.U, e = U.esc, W = U.WARNA;
  const AWAL = "2025-01-01", AKHIR = "2025-12-31";
  const CEPAT = [["Setahun", AWAL, AKHIR], ["Jan–Mar", "2025-01-01", "2025-03-31"], ["Jun–Sep", "2025-06-01", "2025-09-30"], ["Desember", "2025-12-01", AKHIR]];

  const url = new URLSearchParams(location.search);
  let dari = url.has("dari") ? url.get("dari") : AWAL;
  let sampai = url.has("sampai") ? url.get("sampai") : AKHIR;
  let nomor = 0;

  function unduhHref(kota) {
    if (!dari || !sampai || dari > sampai) return null;
    return "/api/analisis.csv?" + new URLSearchParams({ kota: kota, dari: dari, sampai: sampai });
  }

  function kontrol(kota) {
    const href = unduhHref(kota);
    return '<div class="kendali" role="group" aria-label="Rentang tanggal">' +
      '<label class="isian">' + U.ikon("kalender", 18) + 'Dari <input type="date" id="dari" min="' + AWAL + '" max="' + AKHIR + '" value="' + e(dari) + '"></label>' +
      '<label class="isian">Sampai <input type="date" id="sampai" min="' + AWAL + '" max="' + AKHIR + '" value="' + e(sampai) + '"></label>' +
      CEPAT.map(function (c) { return '<button type="button" class="chip" data-cepat="' + c[1] + "|" + c[2] + '" aria-pressed="' + (c[1] === dari && c[2] === sampai) + '" style="min-height:44px">' + c[0] + "</button>"; }).join("") +
      '<div class="renggang"></div><a class="btn gelap" id="unduh" ' + (href ? 'href="' + e(href) + '" download' : 'aria-disabled="true" style="opacity:.5;pointer-events:none"') + ">" + U.ikon("unduh", 18) + "Unduh CSV</a></div>";
  }

  function kerangka(kota) {
    return kontrol(kota) + '<div id="hasil" class="hasil" style="display:flex;flex-direction:column;gap:18px">' + skeleton() + "</div>";
  }
  function skeleton() {
    const b = function (t, r) { return '<div class="skel" style="height:' + t + "px;border-radius:" + (r || 24) + 'px"></div>'; };
    return '<div class="petak">' + b(110, 20) + b(110, 20) + b(110, 20) + b(110, 20) + "</div>" + b(80) + b(280);
  }

  function ubin(label, nilai, catatan, hangat) {
    return '<div class="ubin"><div class="label">' + e(label) + '</div><div class="angka">' + nilai + "</div>" +
      (catatan ? '<div class="catatan' + (hangat ? " hangat" : "") + '">' + e(catatan) + "</div>" : "") + "</div>";
  }

  function kartu(d) {
    const k = d.kartu, bulan = function (b) { return b ? e(b.bulan) : "—"; };
    const nilaiBulan = function (b) { return b ? U.angka(b.hujan, 1, " mm") : "butuh bulan utuh"; };
    return '<div class="petak">' +
      ubin("Rerata suhu", U.angka(k.suhu.nilai, 2, " °C"), k.suhu.catatan) +
      ubin("Total hujan", U.angka(k.hujan.nilai, 1, " mm"), k.hujan.nilai == null ? "hujan tidak lengkap" : k.hujan.catatan) +
      ubin("Bulan terbasah", bulan(k.terbasah), nilaiBulan(k.terbasah)) +
      ubin("Bulan terkering", bulan(k.terkering), nilaiBulan(k.terkering), true) + "</div>";
  }

  function keterangan(d) {
    const i = d.indikator, v = d.valid;
    return '<p class="kecil">' + e(d.kota) + " · " + U.ribuan(d.jam) + " interval jam · rerata kelembapan " + U.angka(i.relative_humidity_2m, 2, "%") +
      " · rerata PM2.5 " + U.angka(i.pm2_5, 2, " µg/m³") + " · nilai valid: suhu " + v.temperature_2m + " / kelembapan " + v.relative_humidity_2m + " / hujan " + v.rain + " / PM2.5 " + v.pm2_5 +
      " · PM2.5 merupakan estimasi model." + (i.rain == null ? " Hujan hanya dijumlahkan jika seluruh jam pada periode itu punya nilai." : "") + "</p>";
  }

  function tabel(d) {
    const bulan = function (b) { return b ? e(b.bulan) + " · " + U.angka(b.hujan, 1, " mm") : "—"; };
    const baris = d.tabel_kota.map(function (r) {
      return '<tr class="' + (r.terpilih ? "pilih" : "") + '"><td class="tebal">' + e(r.kota) + "</td><td>" + U.angka(r.temperature_2m, 2, " °C") + "</td><td>" + U.angka(r.relative_humidity_2m, 2, "%") +
        "</td><td>" + U.angka(r.rain, 1, " mm") + "</td><td>" + U.angka(r.pm2_5, 2, " µg/m³") + "</td><td>" + bulan(r.terbasah) + "</td><td>" + bulan(r.terkering) +
        '</td><td class="tebal">' + (r.r_hujan_pm25.r == null ? "—" : U.angka(r.r_hujan_pm25.r, 3)) + "</td></tr>";
    }).join("");
    return '<section class="kartu"><div class="kepala"><h2>Perbandingan pada tanggal yang sama</h2><span class="kecil">tiga kota, periode terpilih</span></div><div class="gulir">' +
      '<table style="min-width:900px"><thead><tr><th>Kota</th><th>Suhu rata-rata</th><th>Kelembapan</th><th>Hujan</th><th>PM2.5</th><th>Terbasah</th><th>Terkering</th><th>r hujan–PM2.5</th></tr></thead><tbody>' + baris + "</tbody></table></div>" +
      (d.catatan_korelasi ? '<div style="margin-top:14px" class="catatan-kotak hangat" role="note">' + U.ikon("peringatan", 22) + "<div>" + e(d.catatan_korelasi) + "</div></div>" : "") + "</section>";
  }

  function teksR(k) {
    return k.r != null ? "r = " + U.angka(k.r, 3) + " · " + U.ribuan(k.n) + " pasangan" : "Korelasi belum tersedia · " + U.ribuan(k.n) + " pasangan";
  }

  function rangka(d) {
    return kartu(d) + keterangan(d) +
      (d.temuan ? '<section class="kartu rapat"><div style="display:flex;gap:14px;align-items:flex-start"><span style="color:var(--accent)">' + U.ikon("analisis", 28) + '</span><div style="line-height:1.55"><strong>Temuan</strong> · ' + e(d.temuan) + "</div></div></section>" : "") +
      '<section class="kartu"><div class="kepala"><h2>Suhu rata-rata harian</h2><span class="kecil">' + e(d.kota) + ", " + d.harian.length + ' hari</span></div><div id="g-suhu" class="grafik"></div></section>' +
      '<div class="baris"><section class="kartu"><div class="kepala"><h2>Hujan per bulan</h2><span class="kecil">oranye = terkering</span></div><div id="g-hujan" class="grafik"></div></section>' +
      '<section class="kartu"><div class="kepala"><h2>PM2.5 per bulan</h2><span class="kecil">estimasi CAMS, bukan sensor</span></div><div id="g-pm" class="grafik"></div></section></div>' +
      (d.bulan_parsial ? U.catatan(d.bulan_parsial, "hangat") : "") + tabel(d) +
      '<section class="kartu"><div class="kepala"><h2>Hubungan antarvariabel</h2><span class="kecil">korelasi Pearson</span></div><div class="baris">' +
      '<div><div id="g-sebar1" class="grafik"></div><p style="margin-top:6px">' + e(teksR(d.korelasi.suhu_kelembapan)) + '</p></div>' +
      '<div><div id="g-sebar2" class="grafik"></div><p style="margin-top:6px">' + e(teksR(d.korelasi.hujan_pm25)) + "</p></div></div>" +
      '<p class="kecil" style="margin-top:12px">Korelasi Pearson menunjukkan arah hubungan dalam periode terpilih. Pola musiman dan faktor lain dapat memengaruhi keduanya.</p></section>';
  }

  function grafik(d) {
    const kering = d.kartu.terkering ? d.kartu.terkering.kode : null;
    const bln = d.bulanan, label = bln.map(function (b) { return U.waktu.bulanPendek(b.bulan); });
    const sumbuY = function (judul) { return { title: { text: judul, font: { size: 12 } } }; };
    const yAxis = function (judul) { return Object.assign({ gridcolor: W.garis, zeroline: false, fixedrange: true, automargin: true }, sumbuY(judul)); };

    U.gambar(document.getElementById("g-suhu"), [{ type: "scatter", mode: "lines", x: d.harian.map(function (h) { return h.tanggal; }), y: d.harian.map(function (h) { return h.temperature_2m; }),
      line: { color: W.aksen, width: 2.5 }, hovertemplate: "%{x}: %{y:.2f} °C<extra></extra>" }],
      U.tata({ height: 260, yaxis: yAxis("Suhu (°C)") }), "Suhu rata-rata harian " + d.kota + " " + d.dari + " sampai " + d.sampai);

    U.gambar(document.getElementById("g-hujan"), [{ type: "bar", x: label, y: bln.map(function (b) { return b.rain; }),
      marker: { color: bln.map(function (b) { return b.bulan === kering ? W.hangat : W.hujan; }) }, hovertemplate: "%{x}: %{y:.1f} mm<extra></extra>" }],
      U.tata({ height: 240, yaxis: yAxis("Hujan (mm)") }), "Jumlah hujan per bulan " + d.kota + "; bulan terkering berwarna oranye");

    U.gambar(document.getElementById("g-pm"), [{ type: "bar", x: label, y: bln.map(function (b) { return b.pm2_5; }), marker: { color: W.pm },
      hovertemplate: "%{x}: %{y:.1f} µg/m³<extra></extra>" }],
      U.tata({ height: 240, yaxis: yAxis("PM2.5 (µg/m³)") }), "Rerata PM2.5 per bulan " + d.kota + ", estimasi CAMS");

    const sebar = function (id, x, y, xs, ys, warna, tanda, judul) {
      const el = document.getElementById(id);
      if (!x.length) { el.innerHTML = '<div class="kosong"><div class="isi-kosong">Belum ada pasangan data untuk digambar.</div></div>'; el.setAttribute("aria-label", judul + ": belum ada pasangan data"); return; }
      U.gambar(el, [{ type: "scatter", mode: "markers", x: x, y: y, text: tanda, marker: { color: warna, size: 7, opacity: 0.65 }, hovertemplate: "%{text}<br>" + xs + ": %{x:.2f} · " + ys + ": %{y:.2f}<extra></extra>" }],
        U.tata({ height: 260, hovermode: "closest", xaxis: { title: { text: xs, font: { size: 12 } }, gridcolor: W.garis, zeroline: false, fixedrange: true },
          yaxis: yAxis(ys) }), judul);
    };
    const harian = d.harian.filter(function (h) { return h.temperature_2m != null && h.relative_humidity_2m != null; });
    sebar("g-sebar1", harian.map(function (h) { return h.temperature_2m; }), harian.map(function (h) { return h.relative_humidity_2m; }),
      "Suhu (°C)", "Kelembapan (%)", W.aksen, harian.map(function (h) { return h.tanggal; }), "Suhu dan kelembapan harian");
    const utuh = bln.filter(function (b) { return b.bulan_utuh && b.rain != null && b.pm2_5 != null; });
    sebar("g-sebar2", utuh.map(function (b) { return b.rain; }), utuh.map(function (b) { return b.pm2_5; }),
      "Hujan (mm)", "PM2.5 (µg/m³)", W.pm, utuh.map(function (b) { return b.bulan; }), "Hujan dan PM2.5 bulanan");
  }

  async function tampil(kota) {
    const saya = ++nomor, hasil = document.getElementById("hasil");
    const unduh = document.getElementById("unduh"), href = unduhHref(kota);
    if (href) { unduh.setAttribute("href", href); unduh.setAttribute("download", ""); unduh.removeAttribute("aria-disabled"); unduh.style.cssText = ""; }
    else { unduh.removeAttribute("href"); unduh.setAttribute("aria-disabled", "true"); unduh.style.cssText = "opacity:.5;pointer-events:none"; }
    document.querySelectorAll("[data-cepat]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.cepat === dari + "|" + sampai)); });
    const adr = new URL(location.href);
    adr.searchParams.set("dari", dari); adr.searchParams.set("sampai", sampai);
    history.replaceState(null, "", adr);
    if (!sampai) { hasil.innerHTML = U.catatan("Pilih tanggal akhir untuk menghitung ringkasan."); return; }
    if (!dari) { hasil.innerHTML = U.catatan("Pilih tanggal awal untuk menghitung ringkasan."); return; }
    hasil.innerHTML = skeleton();
    try {
      const d = await U.api("/api/analisis", { kota: kota, dari: dari, sampai: sampai });
      if (saya !== nomor) return;
      hasil.innerHTML = rangka(d);
      window.Shell.sub("Arsip per jam ERA5 dan CAMS · " + d.kota + ", " + U.ribuan(d.jam) + " jam");
      grafik(d);
    } catch (err) {
      if (saya === nomor) hasil.innerHTML = U.catatan(err.message, "hangat", err.status === 400 ? "" : U.tombolUlang());
      const ulang = document.getElementById("coba-lagi");
      if (ulang) ulang.addEventListener("click", function () { tampil(kota); });
    }
  }

  function pasang() {
    const ubah = function () {
      dari = document.getElementById("dari").value; sampai = document.getElementById("sampai").value;
      if (dari && sampai && dari > sampai) { document.getElementById("hasil").innerHTML = U.catatan("Tanggal awal tidak boleh setelah tanggal akhir.", "hangat"); return; }
      tampil(window.Shell.kota());
    };
    document.getElementById("dari").addEventListener("change", ubah);
    document.getElementById("sampai").addEventListener("change", ubah);
    document.querySelectorAll("[data-cepat]").forEach(function (b) {
      b.addEventListener("click", function () {
        const p = b.dataset.cepat.split("|"); dari = p[0]; sampai = p[1];
        document.getElementById("dari").value = dari; document.getElementById("sampai").value = sampai;
        tampil(window.Shell.kota());
      });
    });
  }

  async function muat(kota, ctx) {
    pasang();
    await tampil(kota);
  }

  window.Shell.mulai({ kunci: "analisis", judul: "Analisis 2025", sub: "Arsip per jam ERA5 dan CAMS", kerangka: kerangka, muat: muat });
})();
