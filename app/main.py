from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app import db

app = FastAPI(title="WexWeather")

INDEX_PAGE = Path(__file__).parent / "static" / "index.html"


def _today():
    """Today's date in UTC, matching how forecast days are defined."""
    return datetime.now(timezone.utc).date()


@app.get("/", include_in_schema=False)
def index():
    """The web page. It calls /today and /tomorrow from the browser."""
    return FileResponse(INDEX_PAGE)


@app.get("/health")
def health():
    """Liveness check for the host. Deliberately skips the database, so a
    database problem shows up as errors on real endpoints, not a dead app."""
    return {"status": "ok"}


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
