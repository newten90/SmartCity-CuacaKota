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
