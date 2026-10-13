"""Endpoints, driven through FastAPI's TestClient. No server needed."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app import db
from app import main
from app.main import app
from tests.conftest import NEVER_SAVED_DAY

client = TestClient(app)


def test_the_page_is_served_at_the_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="today"' in response.text and 'id="tomorrow"' in response.text


def test_health_needs_no_database():
    assert client.get("/health").json() == {"status": "ok"}


def test_data_range():
    response = client.get("/data-range")
    assert response.status_code == 200
    assert response.json()["days"] > 0


def test_stats_for_a_real_date():
    response = client.get("/stats/9/29")
    assert response.status_code == 200
    assert response.json()["years"] > 0


def test_stats_rejects_a_non_integer_month():
    """422 comes from the int annotation, not from code we wrote."""
    assert client.get("/stats/september/29").status_code == 422


def test_today_returns_the_forecast_and_summary(monkeypatch, test_day, a_forecast):
    monkeypatch.setattr(main, "_today", lambda: test_day)
    db.save_today_forecast(a_forecast)
    db.save_summary({
        "date": test_day,
        "weather_summary": "a weather sentence",
        "on_this_day": "a historical fact",
        "model": "test-model",
    })

    response = client.get("/today")
    assert response.status_code == 200

    body = response.json()
    assert body["forecast"]["max_temp"] == a_forecast["max_temp"]
    assert body["summary"]["weather_summary"] == "a weather sentence"


def test_today_with_nothing_saved_is_nulls_not_an_error(monkeypatch):
    """The first day the app runs has nothing for today. That is normal."""
    monkeypatch.setattr(main, "_today", lambda: NEVER_SAVED_DAY)

    response = client.get("/today")
    assert response.status_code == 200
    assert response.json()["forecast"] is None
    assert response.json()["summary"] is None


def test_tomorrow_reads_the_tomorrow_table(monkeypatch, test_day, a_forecast):
    monkeypatch.setattr(main, "_today", lambda: test_day - timedelta(days=1))
    db.save_tomorrow_forecast(a_forecast)

    body = client.get("/tomorrow").json()
    assert body["date"] == str(test_day)
    assert body["forecast"]["max_temp"] == a_forecast["max_temp"]
