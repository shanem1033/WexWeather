"""One command: pull the latest forecast, summarise it, and show the report.

The pieces already existed - this adds only the display, plus a date argument
so the pipeline can be exercised without waiting for midnight.

Two things worth knowing about the shape of this:

Met Eireann's forecast starts at the current hour, so today always comes back
with fewer than 24 readings and the `hours < 24` guard refuses it. The day this
can *produce* is tomorrow; the day it *shows* is today. That asymmetry is the
constraint, not a bug.

The display reads back from the database rather than using the values produce()
just computed. `--show-only` is then the same code path, and a report that
looks right means the stored data is right - which is what the web layer serves.
"""

import argparse
import textwrap
from datetime import date, datetime, timedelta, timezone

from app import db
from scripts.fetch_forecast import (
    PartialDay,
    fetch_and_save_forecast,
    generate_and_save_summaries,
)

LABEL_WIDTH = 15
WRAP_WIDTH = 78
INDENT = " " * (2 + LABEL_WIDTH)


def _number(value, unit="", places=1):
    """Format a measurement, or `--` when there is no reading.

    NULL means "no reading" everywhere in this project, and it has to survive
    all the way to the display: formatting None with `:.1f` raises TypeError.
    """
    if value is None:
        return "--"
    return f"{value:.{places}f}{unit}"


def _block(label, text):
    """One labelled block, wrapped with a hanging indent under the label."""
    return textwrap.fill(
        text,
        width=WRAP_WIDTH,
        # Without this, "mid-table" wraps as "mid-" / "table" and reads as a typo.
        break_on_hyphens=False,
        initial_indent=f"  {label:<{LABEL_WIDTH}}",
        subsequent_indent=INDENT,
    )


def render_report(day):
    """Print the stored report for `day`. Reads the database; no network."""
    forecast = db.get_forecast(day)
    summary = db.get_summary(day)

    print()
    print(f"WexWeather - {day:%A} {day.day} {day:%B %Y}")
    print()

    if forecast is None and summary is None:
        print(f"  Nothing stored for {day}.")
        print()
        return

    if forecast is None:
        # generate_and_save_summaries bails when there is no forecast, so this
        # should be unreachable. Printing it beats crashing on it.
        print(_block("Forecast", "No forecast stored for this day."))
    else:
        print(_block("Forecast", f"max {_number(forecast['max_temp'], 'C')}   "
                                 f"min {_number(forecast['min_temp'], 'C')}"))
        print(_block("", f"rain {_number(forecast['rain_mm'], 'mm')}   "
                         f"wind {_number(forecast['wind_speed_kt'], 'kt', 0)}   "
                         f"gust {_number(forecast['max_gust_kt'], 'kt', 0)}"))
        print(_block("", f"from {forecast['hours']} hourly readings, "
                         f"fetched {forecast['fetched_at']:%d %b %H:%M}"))

    print()

    if summary is None:
        print(_block("Summary", "No summary generated for this day."))
        print()
        return

    print(_block("Summary", summary["weather_summary"] or "Not generated."))
    print()
    print(_block("On this day", summary["on_this_day"] or "Not generated."))
    print()
    print(_block("", f"{summary['model']}, generated "
                     f"{summary['generated_at']:%d %b %H:%M}"))
    print()


def produce(day):
    """Fetch, save and summarise `day`. Returns True if both steps ran.

    A partial day is reported and swallowed: the point of this command is to
    show the report, so refusing to save must not stop the display.
    """
    try:
        fetch_and_save_forecast(day)
    except PartialDay as error:
        print(error)
        return False

    generate_and_save_summaries(day)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch, summarise and show the daily weather report.",
    )
    parser.add_argument(
        "day",
        nargs="?",
        type=date.fromisoformat,
        help="ISO date, e.g. 2026-10-03. Default: produce tomorrow, show today.",
    )
    parser.add_argument(
        "--show-only",
        action="store_true",
        help="Render what is already stored. No network, no model calls.",
    )
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).date()

    if args.show_only:
        render_report(args.day or today)
        return 0

    produce(args.day or (today + timedelta(days=1)))
    render_report(args.day or today)

    # Always 0, unlike the nightly job: a partial day is information here, not
    # failure. scripts/fetch_forecast.py stays the thing a scheduler calls.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
