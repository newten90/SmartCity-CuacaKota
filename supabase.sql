CREATE TABLE IF NOT EXISTS public.cuaca_sensor (
    kota text NOT NULL CHECK (kota IN ('Bandung', 'Jakarta', 'Surabaya')),
    sensor text NOT NULL CHECK (length(sensor) BETWEEN 1 AND 64),
    waktu timestamptz NOT NULL,
    suhu double precision NOT NULL CHECK (suhu BETWEEN -80 AND 70),
    kelembapan double precision NOT NULL CHECK (kelembapan BETWEEN 0 AND 100),
    PRIMARY KEY (kota, sensor, waktu)
);
CREATE INDEX IF NOT EXISTS cuaca_sensor_kota_waktu ON public.cuaca_sensor (kota, waktu);
ALTER TABLE public.cuaca_sensor ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.cuaca_sensor FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS public.cuaca_online (
    kota text NOT NULL,
    waktu timestamptz NOT NULL,
    temperature_2m double precision NOT NULL,
    relative_humidity_2m double precision NOT NULL CHECK (relative_humidity_2m BETWEEN 0 AND 100),
    precipitation double precision NOT NULL CHECK (precipitation >= 0),
    wind_speed_10m double precision NOT NULL CHECK (wind_speed_10m >= 0),
    weather_code integer NOT NULL,
    pm2_5 double precision CHECK (pm2_5 >= 0),
    sumber text NOT NULL,
    PRIMARY KEY (kota, waktu)
);
ALTER TABLE public.cuaca_online ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.cuaca_online FROM PUBLIC, anon, authenticated;
