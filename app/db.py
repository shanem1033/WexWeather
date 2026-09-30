import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def get_data_range():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT MIN(date) AS first_day, MAX(date) AS last_day, COUNT(*) AS days
            FROM daily_weather
            """
        ).fetchone()


def get_history_for_day(month, day, station_id=1775):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT date, max_temp, min_temp, rain_mm, wind_speed_kt, max_gust_kt
            FROM daily_weather
            WHERE station_id = %(station_id)s
                AND EXTRACT(MONTH FROM date) = %(month)s
                AND EXTRACT(DAY FROM date) = %(day)s
            ORDER BY date 
            """,
            {"station_id": station_id, "month": month, "day": day},
        ).fetchall()


def get_day_stats(month, day, station_id=1775):
    with get_connection() as conn:
            return conn.execute(
                """
                SELECT COUNT(*) AS years,
                    ROUND(AVG(max_temp)::numeric, 1) AS avg_max_temp,
                    MAX(max_temp) AS highest_max_temp,
                    MIN(min_temp) AS lowest_min_temp, 
                    ROUND(AVG(rain_mm)::numeric, 1) as avg_rain_mm
                FROM daily_weather
                WHERE station_id = %(station_id)s
                    AND EXTRACT(MONTH FROM date) = %(month)s
                    AND EXTRACT(DAY FROM date) = %(day)s
                """,
                {"station_id": station_id, "month": month, "day": day},
        ).fetchone()

def get_forecast(day, station_id=1775):
    """Read back the saved forecast for one day, or None if none is saved."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT date, max_temp, min_temp, rain_mm, wind_speed_kt, max_gust_kt,
                   hours, fetched_at
            FROM daily_forecast
            WHERE station_id = %(station_id)s
                AND date = %(day)s
            """,
            {"station_id": station_id, "day": day},
        ).fetchone()


def save_forecast(summary, station_id=1775):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO daily_forecast
                (station_id, date, max_temp, min_temp, rain_mm,
                 wind_speed_kt, max_gust_kt, hours)
            VALUES
                (%(station_id)s, %(date)s, %(max_temp)s, %(min_temp)s, %(rain_mm)s,
                 %(wind_speed_kt)s, %(max_gust_kt)s, %(hours)s)
            ON CONFLICT (station_id, date) DO NOTHING
            """,
            {**summary, "station_id": station_id},
        )
        return cur.rowcount == 1

def get_summary(day, station_id=1775):
    """Read back the saved summary for one day, or None if none is saved."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT weather_summary, on_this_day, model, generated_at
            FROM daily_summary
            WHERE station_id = %(station_id)s
                AND date = %(day)s
            """,
            {"station_id": station_id, "day": day},
        ).fetchone()

def save_summary(summary, station_id=1775):
    """Save one day's summaries. Returns True if a row was inserted."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO daily_summary
                (station_id, date, weather_summary, on_this_day, model)
            VALUES
                (%(station_id)s, %(date)s, %(weather_summary)s, %(on_this_day)s, %(model)s)
            ON CONFLICT (station_id, date) DO NOTHING
            """,
            {**summary, "station_id": station_id},
        )
        return cur.rowcount == 1