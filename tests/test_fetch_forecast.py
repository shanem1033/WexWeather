"""The nightly job's routing: which day goes to which table.

The fetch and the saves are replaced with fakes, so this runs against the saved
XML and writes nothing to the database.
"""

from datetime import date

import pytest

from scripts import fetch_forecast


@pytest.fixture
def saved(monkeypatch, parsed_sample):
    """Run the job offline and record what each save function received."""
    calls = {"today": [], "tomorrow": [], "summary": []}

    monkeypatch.setattr(fetch_forecast, "fetch_forecast", lambda: parsed_sample)
    monkeypatch.setattr(fetch_forecast.db, "save_today_forecast",
                        lambda f: calls["today"].append(f["date"]) or True)
    monkeypatch.setattr(fetch_forecast.db, "save_tomorrow_forecast",
                        lambda f: calls["tomorrow"].append(f["date"]) or True)
    monkeypatch.setattr(fetch_forecast, "generate_and_save_summaries",
                        lambda day: calls["summary"].append(day))
    return calls


def test_one_run_saves_the_next_two_days_to_separate_tables(saved):
    # The sample was fetched on 24 Sept; the 25th and 26th are full days.
    problems = fetch_forecast.run(date(2026, 9, 24))

    assert problems == []
    assert saved["today"] == [date(2026, 9, 25)]
    assert saved["tomorrow"] == [date(2026, 9, 26)]
    assert saved["summary"] == [date(2026, 9, 25)]


def test_a_partial_day_is_reported_without_blocking_the_other(saved):
    # Run as of the 25th: the 26th is full, the 27th has only 20 readings.
    problems = fetch_forecast.run(date(2026, 9, 25))

    assert saved["today"] == [date(2026, 9, 26)]
    assert saved["tomorrow"] == []
    assert len(problems) == 1 and "2026-09-27" in problems[0]
    assert saved["summary"] == [date(2026, 9, 26)]
