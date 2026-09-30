"""Endpoints, driven through FastAPI's TestClient. No server needed."""

from fastapi.testclient import TestClient

from app import db
from app.main import app
from tests.conftest import NEVER_SAVED_DAY

client = TestClient(app)


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


def test_summary_returns_a_saved_row(test_day):
    db.save_summary({
        "date": test_day,
        "weather_summary": "a weather sentence",
        "on_this_day": "a historical fact",
        "model": "test-model",
    })

    response = client.get(f"/summary/{test_day}")
    assert response.status_code == 200

    body = response.json()
    assert body["weather_summary"] == "a weather sentence"
    assert body["on_this_day"] == "a historical fact"


def test_summary_404s_when_nothing_is_saved():
    response = client.get(f"/summary/{NEVER_SAVED_DAY}")
    assert response.status_code == 404
    assert "No summary" in response.json()["detail"]


def test_summary_rejects_an_unparseable_date():
    assert client.get("/summary/not-a-date").status_code == 422


def test_summary_today_resolves_without_error():
    """Whether today has a row depends on whether the job ran, so accept
    either - but never a 500."""
    assert client.get("/summary").status_code in (200, 404)
