CREATE TABLE IF NOT EXISTS stations (
    station_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    county      TEXT,
    latitude    REAL,
    longitude   REAL
);

CREATE TABLE IF NOT EXISTS daily_weather (
    station_id      INTEGER NOT NULL REFERENCES stations(station_id),
    date            DATE NOT NULL,
    max_temp        REAL,
    min_temp        REAL,
    rain_mm         REAL,
    wind_speed_kt   REAL,
    max_gust_kt     REAL,
    sunshine_hours  REAL,
    PRIMARY KEY (station_id, date)
);