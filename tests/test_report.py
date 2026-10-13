"""The one-command report. No network and no model calls.

render_report reads three rows - today's forecast, the summary and tomorrow's
forecast - and each can be absent independently of the others.
"""

from datetime import timedelta

from app import db
from scripts import report
from scripts.report import render_report
from tests.conftest import NEVER_SAVED_DAY

SUMMARY_SENTENCE = "A mid-table day with nothing unusual about it."
FACT_SENTENCE = "1903: The first crossing was completed."


def a_summary(day, weather=SUMMARY_SENTENCE, fact=FACT_SENTENCE):
    return {
        "date": day,
        "weather_summary": weather,
        "on_this_day": fact,
        "model": "test-model",
    }


def test_nothing_stored_says_so_instead_of_raising(capsys):
    render_report(NEVER_SAVED_DAY)
    assert "Nothing stored" in capsys.readouterr().out


def test_forecast_without_a_summary_shows_the_numbers(capsys, test_day, a_forecast):
    db.save_today_forecast(a_forecast)
    render_report(test_day)

    out = capsys.readouterr().out
    assert "10.0C" in out and "5.0C" in out
    assert "24 hourly readings" in out
    assert "No summary generated" in out


def test_both_rows_show_the_numbers_and_both_sentences(capsys, test_day, a_forecast):
    db.save_today_forecast(a_forecast)
    db.save_summary(a_summary(test_day))
    render_report(test_day)

    out = capsys.readouterr().out
    assert "10.0C" in out
    assert SUMMARY_SENTENCE in out
    assert FACT_SENTENCE in out
    assert "test-model" in out


def test_a_summary_with_no_forecast_does_not_crash(capsys, test_day):
    """Unreachable in practice - generate_and_save_summaries bails without a
    forecast - but the display must not depend on that holding."""
    db.save_summary(a_summary(test_day))
    render_report(test_day)

    out = capsys.readouterr().out
    assert "No forecast stored" in out
    assert SUMMARY_SENTENCE in out


def test_a_null_reading_renders_instead_of_raising(capsys, test_day, a_forecast):
    """NULL means "no reading" all the way to the display. Formatting None
    with :.1f raises TypeError, which would take the whole report down."""
    db.save_today_forecast({**a_forecast, "rain_mm": None, "max_gust_kt": None})
    render_report(test_day)

    out = capsys.readouterr().out
    assert "rain --" in out
    assert "gust --" in out


def test_one_sentence_missing_does_not_blank_the_other(capsys, test_day, a_forecast):
    db.save_today_forecast(a_forecast)
    db.save_summary(a_summary(test_day, weather=None))
    render_report(test_day)

    out = capsys.readouterr().out
    assert "Not generated" in out
    assert FACT_SENTENCE in out


def test_a_partial_day_says_so(capsys, test_day, a_forecast):
    db.save_today_forecast({**a_forecast, "hours": 21})
    render_report(test_day)
    assert "Full day not recorded" in capsys.readouterr().out


def test_a_full_day_has_no_note(capsys, test_day, a_forecast):
    db.save_today_forecast(a_forecast)
    render_report(test_day)
    assert "Full day not recorded" not in capsys.readouterr().out


def test_tomorrow_is_read_from_its_own_table(capsys, test_day, a_forecast):
    """The report for the day before TEST_DAY shows TEST_DAY as tomorrow."""
    db.save_tomorrow_forecast(a_forecast)
    render_report(test_day - timedelta(days=1))

    out = capsys.readouterr().out
    assert "Tomorrow" in out and "10.0C" in out
    assert "No forecast stored for this day" in out


def test_produce_reports_problems_instead_of_raising(capsys, monkeypatch):
    """A refused day must leave the display able to run. Monkeypatched rather
    than fetched, to keep the no-network rule."""
    monkeypatch.setattr(report, "run", lambda today: ["Only 9 hours for 1900-01-03, not saving"])

    assert report.produce(NEVER_SAVED_DAY) is False
    assert "not saving" in capsys.readouterr().out
