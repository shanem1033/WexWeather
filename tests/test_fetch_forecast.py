"""The nightly job's routing: which day goes to which table.

The fetch and the saves are replaced with fakes, so this runs against the saved
XML and writes nothing to the database. The sample was fetched at 17:00 UTC on
24 Sept: the 24th has 7 hours left, the 25th and 26th are full, the 27th has 20.
"""

from datetime import date

import pytest

from scripts import fetch_forecast


@pytest.fixture
def saved(monkeypatch, parsed_sample):
    """Run the job offline and record (date, hours) for every save."""
    calls = {"today": [], "tomorrow": [], "summary": []}

    def recorder(table):
        def save(forecast):
            calls[table].append((forecast["date"], forecast["hours"]))
            return True
        return save

    monkeypatch.setattr(fetch_forecast, "fetch_forecast", lambda: parsed_sample)
    monkeypatch.setattr(fetch_forecast.db, "save_today_forecast", recorder("today"))
    monkeypatch.setattr(fetch_forecast.db, "save_tomorrow_forecast", recorder("tomorrow"))
    monkeypatch.setattr(fetch_forecast, "generate_and_save_summaries",
                        lambda day: calls["summary"].append(day))
    return calls


def test_a_run_saves_its_two_days_and_fills_in_what_is_shown_now(saved):
    problems = fetch_forecast.run(date(2026, 9, 24))

    assert problems == []
    # Today (24th) is a fill-in from the 7 hours left; the 25th is the real target.
    assert saved["today"] == [(date(2026, 9, 24), 7), (date(2026, 9, 25), 24)]
    assert saved["tomorrow"] == [(date(2026, 9, 25), 24), (date(2026, 9, 26), 24)]
    assert saved["summary"] == [date(2026, 9, 24), date(2026, 9, 25)]


def test_a_partial_target_day_is_saved_and_reported(saved):
    # Run as of the 25th: the 27th, a real target, has only 20 readings.
    problems = fetch_forecast.run(date(2026, 9, 25))

    assert (date(2026, 9, 27), 20) in saved["tomorrow"]
    assert len(problems) == 1 and "2026-09-27" in problems[0]


def test_a_partial_fill_in_is_not_a_problem(saved):
    """The 24th is partial, but it is a fill-in, so partial is expected."""
    assert fetch_forecast.run(date(2026, 9, 24)) == []


def test_a_day_with_no_readings_is_not_saved(saved):
    # The sample ends on 4 Oct, so nothing exists for the 5th or 6th.
    problems = fetch_forecast.run(date(2026, 10, 4))

    saved_days = [d for d, _ in saved["today"] + saved["tomorrow"]]
    assert date(2026, 10, 5) not in saved_days
    assert date(2026, 10, 6) not in saved_days
    assert len(problems) == 2
