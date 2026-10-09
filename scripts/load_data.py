import csv
from datetime import date, datetime

from app import db
from app.config import STATION

CSV_PATH = "data/wexford_daily.csv"
START_DATE = date(2016, 1, 1)

# Column positions in CSV from 0
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
            rows.append({
                "station_id": STATION["station_id"],
                "date": day,
                "max_temp": to_float(row[COL_MAXTP]),
                "min_temp": to_float(row[COL_MINTP]),
                "rain_mm": to_float(row[COL_RAIN]),
                "wind_speed_kt": to_float(row[COL_WDSP]),
                "max_gust_kt": to_float(row[COL_HG]),
            })
    return rows


def main():
    rows = read_rows(CSV_PATH)

    # The station must exist first: every daily_weather row references it.
    db.save_station(STATION)
    added = db.save_weather_days(rows)

    print(f"Read {len(rows)} days, {added} new")


if __name__ == "__main__":
    main()
