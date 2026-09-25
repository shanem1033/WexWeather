from datetime import datetime, timedelta, timezone

from app.db import save_forecast
from app.forecast import fetch_forecast_xml, parse_forecast, summarise_day

LAT, LON = 52.298, -6.497  # Johnstown Castle II


def main():
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    instants, rain = parse_forecast(fetch_forecast_xml(LAT, LON))
    summary = summarise_day(instants, rain, tomorrow)

    if summary["hours"] < 24:
        raise SystemExit(f"Only {summary['hours']} hours for {tomorrow}, not saving")

    if save_forecast(summary):
        print(f"Saved forecast for {tomorrow}: {summary}")
    else:
        print(f"Forecast for {tomorrow} already saved, skipped")


if __name__ == "__main__":
    main()