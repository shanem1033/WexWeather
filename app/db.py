# This file is the only place where the app directly connects to the DB, all other files call these functions and get plain python values back
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.config import DATABASE_URL, STATION_ID


def get_connection():
    # Without a timeout an unreachable database hangs the request forever
    # instead of failing with an error.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def get_data_range():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT MIN(date) AS first_day, MAX(date) AS last_day, COUNT(*) AS days
            FROM daily_weather
            """
        ).fetchone()


def get_history_for_day(month, day, station_id=STATION_ID):
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


def get_day_stats(month, day, station_id=STATION_ID):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT COUNT(*) AS years,
                ROUND(AVG(max_temp)::numeric, 1) AS avg_max_temp,
                MAX(max_temp) AS highest_max_temp,
                MIN(min_temp) AS lowest_min_temp,
                ROUND(AVG(rain_mm)::numeric, 1) AS avg_rain_mm
            FROM daily_weather
            WHERE station_id = %(station_id)s
                AND EXTRACT(MONTH FROM date) = %(month)s
                AND EXTRACT(DAY FROM date) = %(day)s
            """,
            {"station_id": station_id, "month": month, "day": day},
        ).fetchone()


def save_station(station):
    """Add a station if it is not already stored. Returns True if a row was inserted."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO stations (station_id, name, county, latitude, longitude)
            VALUES (%(station_id)s, %(name)s, %(county)s, %(latitude)s, %(longitude)s)
            ON CONFLICT (station_id) DO NOTHING
            """,
            station,
        )
        return cur.rowcount == 1


def save_weather_days(days):
    """Save observed days, skipping any already stored. Returns how many were new."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO daily_weather
                    (station_id, date, max_temp, min_temp, rain_mm,
                     wind_speed_kt, max_gust_kt)
                VALUES
                    (%(station_id)s, %(date)s, %(max_temp)s, %(min_temp)s, %(rain_mm)s,
                     %(wind_speed_kt)s, %(max_gust_kt)s)
                ON CONFLICT (station_id, date) DO NOTHING
                """,
                days,
            )
            return cur.rowcount


def get_today_forecast(day, station_id=STATION_ID):
    """The forecast saved the night before `day`, or None if none is saved."""
    return _get_forecast("forecast_today", day, station_id)


def save_today_forecast(forecast, station_id=STATION_ID):
    """Save the forecast to show on its own day. Returns True if a row was inserted."""
    return _save_forecast("forecast_today", forecast, station_id)


def get_tomorrow_forecast(day, station_id=STATION_ID):
    """The forecast saved two nights before `day`, or None if none is saved."""
    return _get_forecast("forecast_tomorrow", day, station_id)


def save_tomorrow_forecast(forecast, station_id=STATION_ID):
    """Save the forecast to show the day before. Returns True if a row was inserted."""
    return _save_forecast("forecast_tomorrow", forecast, station_id)


# Both forecast tables have the same columns, so one query serves both.
# sql.Identifier quotes the table name safely; a %(name)s parameter can only
# stand in for a value, never for a table.
def _get_forecast(table, day, station_id):
    query = sql.SQL(
        """
        SELECT date, max_temp, min_temp, rain_mm, wind_speed_kt, max_gust_kt,
               hours, hours >= 24 AS full_day, fetched_at
        FROM {table}
        WHERE station_id = %(station_id)s
            AND date = %(day)s
        """
    ).format(table=sql.Identifier(table))

    with get_connection() as conn:
        return conn.execute(query, {"station_id": station_id, "day": day}).fetchone()


def _save_forecast(table, forecast, station_id):
    query = sql.SQL(
        """
        INSERT INTO {table}
            (station_id, date, max_temp, min_temp, rain_mm,
             wind_speed_kt, max_gust_kt, hours)
        VALUES
            (%(station_id)s, %(date)s, %(max_temp)s, %(min_temp)s, %(rain_mm)s,
             %(wind_speed_kt)s, %(max_gust_kt)s, %(hours)s)
        ON CONFLICT (station_id, date) DO NOTHING
        """
    ).format(table=sql.Identifier(table))

    with get_connection() as conn:
        cur = conn.execute(query, {**forecast, "station_id": station_id})
        return cur.rowcount == 1


def get_summary(day, station_id=STATION_ID):
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


def save_summary(summary, station_id=STATION_ID):
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
