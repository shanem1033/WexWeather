from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from app import db

app = FastAPI(title="WexWeather")


def _today():
    """Today's date in UTC, matching how forecast days are defined."""
    return datetime.now(timezone.utc).date()


@app.get("/data-range")
def data_range():
    return db.get_data_range()


@app.get("/stats/{month}/{day}")
def stats(month: int, day: int):
    return db.get_day_stats(month, day)


@app.get("/today")
def today():
    """Today's forecast and summary, both saved last night.

    A missing row is null rather than a 404: on the first day the app runs,
    nothing has been saved for today yet, and that is a normal state.
    """
    day = _today()
    return {
        "date": day,
        "forecast": db.get_today_forecast(day),
        "summary": db.get_summary(day),
    }


@app.get("/tomorrow")
def tomorrow():
    """Tomorrow's forecast, saved the night before last."""
    day = _today() + timedelta(days=1)
    return {
        "date": day,
        "forecast": db.get_tomorrow_forecast(day),
    }
