/* Ikon garis, format angka Indonesia, pemanggil API, dan pembantu grafik. Tanpa framework. */
(function () {
  "use strict";

  const IKON = {
    cuaca: '<path d="M4 11l8-6.5 8 6.5M6 9.5V20h12V9.5"/>',
    analisis: '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6"/>',
    riwayat: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4.5l3 2"/>',
    kota: '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    "cerah-berawan": '<path d="M8.5 4.5v1.4M3.6 9.2h1.4M5 5.7l1 1M12 5.7l-1 1"/><path d="M5.6 11.2a3.6 3.6 0 0 1 6.4-3"/><path d="M8 19h9a3.6 3.6 0 0 0 .3-7.2 5 5 0 0 0-9.6.9A3.2 3.2 0 0 0 8 19z"/>',
    cerah: '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>',
    berawan: '<path d="M7 18.5h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1A3.6 3.6 0 0 0 7 18.5z"/>',
    gerimis: '<path d="M7 14h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1A3.6 3.6 0 0 0 7 14z"/><path d="M9 17.5l-.8 2M14 17.5l-.8 2"/>',
    hujan: '<path d="M7 15h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1A3.6 3.6 0 0 0 7 15z"/><path d="M8.5 18l-1 2.5M12.5 18l-1 2.5M16.5 18l-1 2.5"/>',
    petir: '<path d="M7 14h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1A3.6 3.6 0 0 0 7 14z"/><path d="M12.5 15l-2 3.5h3l-2 3.5"/>',
    kabut: '<path d="M7 13h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1A3.6 3.6 0 0 0 7 13z"/><path d="M5 16.5h14M8 20h8"/>',
    netral: '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z"/>',
    lembap: '<path d="M12 3.5s6 6.4 6 10.5a6 6 0 0 1-12 0c0-4.1 6-10.5 6-10.5z"/>',
    angin: '<path d="M3 9h11a2.5 2.5 0 1 0-2.5-2.5M3 13h15a2.5 2.5 0 1 1-2.5 2.5M3 17h7"/>',
    pm: '<path d="M4 8h9a2 2 0 1 0-2-2M4 12h13a2 2 0 1 1-2 2M4 16h6"/><circle cx="18.5" cy="7" r="1"/>',
    terbit: '<path d="M4 18h16M7 14a5 5 0 0 1 10 0M12 4v5M9.5 6.5L12 4l2.5 2.5"/>',
    kalender: '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    unduh: '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
    basisdata: '<ellipse cx="12" cy="6" rx="7" ry="2.6"/><path d="M5 6v12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6M5 12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.5v.5"/>',
    peringatan: '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5M12 17.5v.5"/>',
    ulang: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>',
  };

  function ikon(nama, ukuran, tebal, warna) {
    const isi = IKON[nama] || IKON.netral;
    return '<svg width="' + (ukuran || 24) + '" height="' + (ukuran || 24) + '" viewBox="0 0 24 24" fill="none" stroke="' +
      (warna || "currentColor") + '" stroke-width="' + (tebal || 1.8) + '" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + isi + "</svg>";
  }

  // Semua teks dari API dilewatkan esc() sebelum masuk HTML.
  function esc(teks) {
    return String(teks == null ? "" : teks).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  const pemformat = {};
  function angka(nilai, digit, satuan) {
    if (nilai == null || Number.isNaN(nilai)) return "—";
    const d = digit == null ? 1 : digit;
    pemformat[d] = pemformat[d] || new Intl.NumberFormat("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d });
    return pemformat[d].format(nilai).replace("-", "−") + (satuan || "");
  }
  const bulat = function (nilai, satuan) { return angka(nilai, 0, satuan); };
  const ribuan = function (nilai) { return angka(nilai, 0); };

  const BULAN_PENDEK = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  // Waktu dari API sudah WIB dan tidak dikonversi lewat Date, jadi tidak tergantung zona waktu peramban.
  function bagian(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(iso || "");
    return m ? { y: m[1], mo: m[2], d: m[3], h: m[4], mi: m[5] } : null;
  }
  const waktu = {
    jam: function (iso) { const p = bagian(iso); return p ? p.h + ":" + p.mi : "—"; },
    tgl: function (iso) { const p = bagian(iso); return p ? p.d + "/" + p.mo : "—"; },
    tglJam: function (iso) { const p = bagian(iso); return p ? p.d + "/" + p.mo + " " + p.h + ":" + p.mi : "—"; },
    lengkap: function (iso) { const p = bagian(iso); return p ? p.d + "/" + p.mo + "/" + p.y + " " + p.h + ":" + p.mi + " WIB" : "—"; },
    tanggalPendek: function (iso) { const p = bagian(iso); return p ? Number(p.d) + " " + BULAN_PENDEK[Number(p.mo) - 1] + " " + p.y : "—"; },
    bulanPendek: function (kode) { return BULAN_PENDEK[Number(String(kode).slice(5, 7)) - 1] || kode; },
  };

  async function api(path, params) {
    const q = new URLSearchParams();
    Object.keys(params || {}).forEach(function (k) { if (params[k] != null && params[k] !== "") q.set(k, params[k]); });
    let respons;
    try {
      respons = await fetch(path + (q.toString() ? "?" + q : ""), { headers: { Accept: "application/json" } });
    } catch (e) {
      const galat = new Error("Tidak dapat menghubungi server. Periksa koneksi internet lalu coba lagi.");
      galat.status = 0;
      throw galat;
    }
    let isi = null;
    try { isi = await respons.json(); } catch (e) { /* bukan JSON */ }
    if (!respons.ok) {
      const galat = new Error((isi && isi.pesan) || "Permintaan gagal (" + respons.status + ").");
      galat.status = respons.status;
      throw galat;
    }
    return isi;
  }

  function skeleton(tinggi, lebar) {
    return '<div class="skel" style="height:' + tinggi + "px;width:" + (lebar || "100%") + '"></div>';
  }

  function catatan(teks, jenis, aksi) {
    return '<div class="catatan-kotak' + (jenis === "hangat" ? " hangat" : "") + '" role="' + (jenis === "hangat" ? "alert" : "status") + '">' +
      ikon(jenis === "hangat" ? "peringatan" : "info", 22) + "<div><div>" + esc(teks) + "</div>" + (aksi ? '<div class="aksi">' + aksi + "</div>" : "") + "</div></div>";
  }

  function tombolUlang(id) {
    return '<button type="button" class="btn" id="' + (id || "coba-lagi") + '">' + ikon("ulang", 18) + "Coba lagi</button>";
  }

  // ---------- grafik (Plotly.js dimuat dari CDN resmi) ----------
  const WARNA = { aksen: "#2459D6", lunak: "#E3EBFB", hujan: "#7FA6F2", pm: "#0F766E", hangat: "#B45309", garis: "#D7E0EA", teks: "#4A586B" };

  function tata(opsi) {
    const o = opsi || {};
    return Object.assign({
      margin: { t: 10, r: 14, b: 38, l: 48 },
      font: { family: "Manrope, system-ui, sans-serif", size: 12, color: WARNA.teks },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", showlegend: false, hovermode: "x unified", separators: ",.",
      xaxis: { gridcolor: WARNA.garis, linecolor: WARNA.garis, zeroline: false, fixedrange: true },
      yaxis: { gridcolor: WARNA.garis, zeroline: false, fixedrange: true, automargin: true },
      hoverlabel: { font: { family: "Manrope, system-ui, sans-serif" } },
    }, o);
  }

  function gambar(el, data, tataan, label) {
    if (!el) return;
    el.setAttribute("role", "img");
    if (label) el.setAttribute("aria-label", label);
    if (!window.Plotly) {
      el.innerHTML = catatan("Grafik tidak dapat dimuat. Tabel di halaman ini tetap menampilkan datanya.", "hangat");
      return;
    }
    window.Plotly.newPlot(el, data, tataan, { displayModeBar: false, responsive: true });
  }

  window.U = { ikon: ikon, esc: esc, angka: angka, bulat: bulat, ribuan: ribuan, waktu: waktu, api: api, skeleton: skeleton,
    catatan: catatan, tombolUlang: tombolUlang, WARNA: WARNA, tata: tata, gambar: gambar };
})();
