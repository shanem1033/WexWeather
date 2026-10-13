"""Nightly job, run at 20:17 UTC by GitHub Actions.

One fetch saves two forecasts. Run on the 9th, it saves:

- the 10th to forecast_today: shown as today's forecast on the 10th, and the
  one the summary is written from
- the 11th to forecast_tomorrow: shown as tomorrow's forecast on the 10th

Both are complete hourly days at that point.

It also fills anything the app is showing right now that is missing: today in
forecast_today and the day after in forecast_tomorrow. On time, those already
exist and are skipped. After a late run - one that slips past midnight acts
as the next night's - they are the rows that would otherwise be blank.

Today is never a full day, because the feed starts at the current hour, so a
filled-in today is saved from the hours that are left and flagged as not a
full day. Something is better than nothing, as long as it says so.
"""

from datetime import datetime, timedelta, timezone

from app import db, onthisday, summary
from app.config import STATION
from app.forecast import fetch_forecast_xml, parse_forecast, summarise_day


def fetch_forecast():
    """Download and parse the full forecast: several days of readings."""
    xml_text = fetch_forecast_xml(STATION["latitude"], STATION["longitude"])
    return parse_forecast(xml_text)


def save_forecast_day(instants, rain, day, save, label):
    """Summarise `day` and store it with `save`. Returns the hours it covers.

    A day with fewer than 24 readings is still saved; the database flags it
    as not a full day. A day with none is skipped: a row of nulls says nothing.
    """
    forecast = summarise_day(instants, rain, day)

    if forecast["hours"] == 0:
        print(f"No readings for {day}, nothing to save as {label}")
        return 0

    note = "" if forecast["hours"] >= 24 else " (full day not recorded)"
    if save(forecast):
        print(f"Saved {label} forecast for {day}{note}: {forecast}")
    else:
        print(f"{label.capitalize()} forecast for {day} already saved, skipped")
    return forecast["hours"]


def generate_and_save_summaries(day):
    """Write the day's two sentences, unless they are already stored."""
    if db.get_summary(day) is not None:
        print(f"Summary for {day} already saved, skipped")
        return

    context = summary.build_context(day)
    if context is None:
        print(f"No forecast saved for {day}, nothing to summarise")
        return

    weather = summary.summarise(context)
    fact = summary.summarise_on_this_day(onthisday.fetch_events(day))

    if weather is None and fact is None:
        print(f"No summary for {day}: nothing generated")
        return

    db.save_summary({
        "date": day,
        "weather_summary": weather,
        "on_this_day": fact,
        "model": summary.SUMMARY_MODEL,
    })
    print(f"Saved summary for {day}")
    print(f"  weather:     {weather}")
    print(f"  on this day: {fact}")


def run(today):
    """Save the forecasts and summaries. Returns a list of problems, empty if none.

    Only the two days this run exists for are expected to be full, so only
    they count as problems when partial. The fill-ins are partial by nature.
    """
    instants, rain = fetch_forecast()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    # (day, save, label, expected to be a full day)
    targets = [
        (today, db.save_today_forecast, "today", False),
        (tomorrow, db.save_today_forecast, "today", True),
        (tomorrow, db.save_tomorrow_forecast, "tomorrow", False),
        (day_after, db.save_tomorrow_forecast, "tomorrow", True),
    ]

    problems = []
    for day, save, label, expected_full in targets:
        hours = save_forecast_day(instants, rain, day, save, label)
        if expected_full and hours < 24:
            problems.append(f"Only {hours} hours for {day} ({label} forecast)")

    # Each bails out by itself if already saved or there is no forecast.
    generate_and_save_summaries(today)
    generate_and_save_summaries(tomorrow)
    return problems


def main():
    problems = run(datetime.now(timezone.utc).date())
    if problems:
        # Non-zero exit, so the scheduler records a failed night.
        raise SystemExit("; ".join(problems))


if __name__ == "__main__":
    main()
