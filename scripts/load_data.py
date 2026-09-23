import csv
import os
from datetime import date, datetime

import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

CSV_PATH = "data/wexford_daily.csv"
START_DATE = date(2016, 1, 1)


STATION = {
    "station_id": 1775,
    "name": "Johnstown Castle II",
    "county": "Wexford",
    "latitude": 52.298,
    "longitude": -6.497,
}

# Column posiotions in CSV from 0
COL_DATE, COL_MAXTP, COL_MINTP, COL_RAIN, COL_WDSP, COL_HG = 0, 2, 4, 8, 10, 16


def to_float(value):
    """Convert a CSV cell to a float, or None if it's blank."""
    value = value.strip()
    return float(value) if value else None

def read_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        # skip notes at top until reach header row
        for line in f:
            if line.startswith("date,"):
                break

        for row in csv.reader(f):
            if not row:
                continue
            day = datetime.strptime(row[COL_DATE], "%d-%b-%Y").date()
            if day < START_DATE:
                continue
            rows.append((
                STATION["station_id"],
                day,
                to_float(row[COL_MAXTP]),
                to_float(row[COL_MINTP]),
                to_float(row[COL_RAIN]),
                to_float(row[COL_WDSP]),
                to_float(row[COL_HG]),
            ))
    return rows

def main():
    rows = read_rows(CSV_PATH)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stations (station_id, name, county, latitude, longitude)
                VALUES (%(station_id)s, %(name)s, %(county)s, %(latitude)s, %(longitude)s)
                ON CONFLICT (station_id) DO NOTHING
                """,
                STATION,
            )
            cur.executemany(
                """
                INSERT INTO daily_weather
                    (station_id, date, max_temp, min_temp, rain_mm, wind_speed_kt, max_gust_kt)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (station_id, date) DO NOTHING
                """,
                rows,
            )

    print(f"Processed {len(rows)} rows")


if __name__ == "__main__":
    main()