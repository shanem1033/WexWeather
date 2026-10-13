"""Nightly job, run at 20:17 UTC by GitHub Actions.

One fetch saves two forecasts. Run on the 9th, it saves:

- the 10th to forecast_today: shown as today's forecast on the 10th, and the
  one the summary is written from
- the 11th to forecast_tomorrow: shown as tomorrow's forecast on the 10th

Both are complete hourly days at that point. Today itself never is, because
the feed starts at the current hour.
"""

from datetime import datetime, timedelta, timezone

from app import db, onthisday, summary
from app.config import STATION
from app.forecast import fetch_forecast_xml, parse_forecast, summarise_day


class PartialDay(Exception):
    """The forecast has fewer than 24 readings for the requested day."""


def fetch_forecast():
    """Download and parse the full forecast: several days of readings."""
    xml_text = fetch_forecast_xml(STATION["latitude"], STATION["longitude"])
    return parse_forecast(xml_text)


def save_forecast_day(instants, rain, day, save, label):
    """Summarise `day` and store it with `save`. Returns True if a row was written."""
    forecast = summarise_day(instants, rain, day)

    if forecast["hours"] < 24:
        raise PartialDay(f"Only {forecast['hours']} hours for {day}, not saving {label}")

    if save(forecast):
        print(f"Saved {label} forecast for {day}: {forecast}")
        return True

    print(f"{label.capitalize()} forecast for {day} already saved, skipped")
    return False


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
    """Save both forecasts and the summary. Returns a list of problems, empty if none.

    A partial day is collected rather than raised, so one bad day cannot stop
    the other from being saved or the summary from being written.
    """
    instants, rain = fetch_forecast()
    problems = []

    days = [
        (today + timedelta(days=1), db.save_today_forecast, "today"),
        (today + timedelta(days=2), db.save_tomorrow_forecast, "tomorrow"),
    ]
    for day, save, label in days:
        try:
            save_forecast_day(instants, rain, day, save, label)
        except PartialDay as error:
            problems.append(str(error))

    # Bails out by itself if the today forecast was not saved.
    generate_and_save_summaries(today + timedelta(days=1))
    return problems


def main():
    problems = run(datetime.now(timezone.utc).date())
    if problems:
        # Non-zero exit, so the scheduler records a failed night.
        raise SystemExit("; ".join(problems))


if __name__ == "__main__":
    main()
