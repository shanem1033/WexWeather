"""Database access. Reads are harmless; writes use a sentinel date and clean up."""

from app import db
from tests.conftest import NEVER_SAVED_DAY


def test_every_read_function_runs():
    """The smoke test.

    Two shipped bugs would have been caught here the moment they appeared: a
    SELECT naming a column that had been dropped, and a query that ignored its
    date argument. Neither needed a clever assertion - just calling the
    function was enough.
    """
    assert db.get_data_range()["days"] > 0
    assert isinstance(db.get_history_for_day(9, 29), list)
    assert db.get_day_stats(9, 29) is not None
    assert db.get_forecast(NEVER_SAVED_DAY) is None
    assert db.get_summary(NEVER_SAVED_DAY) is None


def test_history_rows_carry_every_expected_column():
    rows = db.get_history_for_day(9, 29)
    assert rows, "29 September should have history"
    expected = {"date", "max_temp", "min_temp", "rain_mm", "wind_speed_kt", "max_gust_kt"}
    assert expected <= set(rows[0])


def test_save_forecast_reports_whether_it_inserted(test_day, a_forecast):
    """Regression: this once returned a Cursor, which is always truthy, so the
    nightly log claimed a save every night."""
    first = db.save_forecast(a_forecast)
    second = db.save_forecast(a_forecast)

    assert first is True
    assert second is False


def test_get_forecast_filters_by_date(test_day, a_forecast):
    """Regression: the query once ignored its date and returned the first row."""
    db.save_forecast(a_forecast)

    assert db.get_forecast(test_day)["date"] == test_day
    assert db.get_forecast(NEVER_SAVED_DAY) is None


def test_saved_forecast_keeps_its_values(test_day, a_forecast):
    db.save_forecast(a_forecast)
    row = db.get_forecast(test_day)

    assert row["max_temp"] == a_forecast["max_temp"]
    assert row["hours"] == 24
    assert row["fetched_at"] is not None


def test_save_summary_round_trips(test_day):
    written = db.save_summary({
        "date": test_day,
        "weather_summary": "a weather sentence",
        "on_this_day": "a historical fact",
        "model": "test-model",
    })
    assert written is True

    row = db.get_summary(test_day)
    assert row["weather_summary"] == "a weather sentence"
    assert row["on_this_day"] == "a historical fact"
    assert row["model"] == "test-model"
    assert row["generated_at"] is not None, "the column default should fill this"


def test_save_summary_does_not_overwrite(test_day):
    first = {"date": test_day, "weather_summary": "original",
             "on_this_day": None, "model": "test-model"}
    second = {**first, "weather_summary": "replacement"}

    assert db.save_summary(first) is True
    assert db.save_summary(second) is False
    assert db.get_summary(test_day)["weather_summary"] == "original"


def test_one_sentence_may_be_null(test_day):
    """The model can fail on one call and succeed on the other."""
    db.save_summary({
        "date": test_day,
        "weather_summary": "only the weather worked",
        "on_this_day": None,
        "model": "test-model",
    })
    assert db.get_summary(test_day)["on_this_day"] is None
