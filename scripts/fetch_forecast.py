from datetime import datetime, timedelta, timezone

from app import db, onthisday, summary
from app.forecast import fetch_forecast_xml, parse_forecast, summarise_day

LAT, LON = 52.298, -6.497  # Johnstown Castle II


def fetch_and_save_forecast(day):
    """Fetch the forecast and save `day`. Returns True if a row was written."""
    instants, rain = parse_forecast(fetch_forecast_xml(LAT, LON))
    forecast = summarise_day(instants, rain, day)

    if forecast["hours"] < 24:
        raise SystemExit(f"Only {forecast['hours']} hours for {day}, not saving")

    if db.save_forecast(forecast):
        print(f"Saved forecast for {day}: {forecast}")
        return True

    print(f"Forecast for {day} already saved, skipped")
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


def main():
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    fetch_and_save_forecast(tomorrow)
    generate_and_save_summaries(tomorrow)


if __name__ == "__main__":
    main()
