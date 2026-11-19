"""Kode cuaca WMO dari Open-Meteo menjadi teks Indonesia dan kunci ikon garis (SVG di static/js/ikon.js)."""

CONDITIONS = {
    0: ("cerah", "Cerah"), 1: ("cerah-berawan", "Sebagian besar cerah"), 2: ("cerah-berawan", "Cerah berawan"),
    3: ("berawan", "Berawan"), 45: ("kabut", "Berkabut"), 48: ("kabut", "Kabut beku"),
    51: ("gerimis", "Gerimis ringan"), 53: ("gerimis", "Gerimis"), 55: ("hujan", "Gerimis lebat"),
    61: ("gerimis", "Hujan ringan"), 63: ("hujan", "Hujan sedang"), 65: ("hujan", "Hujan lebat"),
    80: ("gerimis", "Hujan lokal ringan"), 81: ("hujan", "Hujan lokal sedang"), 82: ("hujan", "Hujan lokal lebat"),
    95: ("petir", "Badai petir"), 96: ("petir", "Petir dan hujan es"), 99: ("petir", "Petir dan hujan es lebat"),
}


def condition(code):
    return CONDITIONS.get(code, ("netral", "Kondisi belum tersedia"))
