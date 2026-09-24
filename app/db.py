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
            SELECT date, max_temp, min_temp, rain_mm, wind_speed_kt, max_gust_kt, sunshine_hours
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