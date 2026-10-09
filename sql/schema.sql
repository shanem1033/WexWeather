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
    PRIMARY KEY (station_id, date)
);

-- Saved the night before `date` and shown as that day's forecast. The only
-- forecast the summaries are built from.
CREATE TABLE IF NOT EXISTS forecast_today (
    station_id      INTEGER NOT NULL REFERENCES stations(station_id),
    date            DATE NOT NULL,
    max_temp        REAL,
    min_temp        REAL,
    rain_mm         REAL,
    wind_speed_kt   REAL,
    max_gust_kt     REAL,
    hours           INTEGER NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (station_id, date)
);

-- Saved two nights before `date` and only ever shown as "tomorrow".
CREATE TABLE IF NOT EXISTS forecast_tomorrow (
    station_id      INTEGER NOT NULL REFERENCES stations(station_id),
    date            DATE NOT NULL,
    max_temp        REAL,
    min_temp        REAL,
    rain_mm         REAL,
    wind_speed_kt   REAL,
    max_gust_kt     REAL,
    hours           INTEGER NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (station_id, date)
);

CREATE TABLE IF NOT EXISTS daily_summary (
    station_id      INTEGER NOT NULL REFERENCES stations(station_id),
    date            DATE NOT NULL,
    weather_summary TEXT,
    on_this_day     TEXT,
    model           TEXT NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (station_id, date)
);