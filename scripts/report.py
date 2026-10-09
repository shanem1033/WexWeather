"""One command: run the nightly job now, then show the report.

The job saves forecasts for the next two days, never today, so a run shows its
results from tomorrow onwards. The date argument shows any stored day.

The display reads back from the database rather than using the values the job
just computed. `--show-only` is then the same code path, and a report that
looks right means the stored data is right - which is what the web layer serves.
"""

import argparse
import textwrap
from datetime import date, datetime, timedelta, timezone

from app import db
from scripts.fetch_forecast import run

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


def _forecast_block(label, forecast):
    """The three lines of numbers for one stored forecast row."""
    return "\n".join([
        _block(label, f"max {_number(forecast['max_temp'], 'C')}   "
                      f"min {_number(forecast['min_temp'], 'C')}"),
        _block("", f"rain {_number(forecast['rain_mm'], 'mm')}   "
                   f"wind {_number(forecast['wind_speed_kt'], 'kt', 0)}   "
                   f"gust {_number(forecast['max_gust_kt'], 'kt', 0)}"),
        _block("", f"from {forecast['hours']} hourly readings, "
                   f"fetched {forecast['fetched_at']:%d %b %H:%M}"),
    ])


def render_report(day):
    """Print the stored report for `day`. Reads the database; no network."""
    forecast = db.get_today_forecast(day)
    summary = db.get_summary(day)
    tomorrow = db.get_tomorrow_forecast(day + timedelta(days=1))

    print()
    print(f"WexWeather - {day:%A} {day.day} {day:%B %Y}")
    print()

    if forecast is None and summary is None and tomorrow is None:
        print(f"  Nothing stored for {day}.")
        print()
        return

    if forecast is None:
        print(_block("Forecast", "No forecast stored for this day."))
    else:
        print(_forecast_block("Forecast", forecast))
    print()

    if summary is None:
        print(_block("Summary", "No summary generated for this day."))
    else:
        print(_block("Summary", summary["weather_summary"] or "Not generated."))
        print()
        print(_block("On this day", summary["on_this_day"] or "Not generated."))
        print()
        print(_block("", f"{summary['model']}, generated "
                         f"{summary['generated_at']:%d %b %H:%M}"))
    print()

    if tomorrow is None:
        print(_block("Tomorrow", "No forecast stored for tomorrow."))
    else:
        print(_forecast_block("Tomorrow", tomorrow))
    print()


def produce(today):
    """Run the nightly job as of `today`. Returns True if nothing was refused.

    Problems are printed, not raised: the point of this command is to show
    the report, so a refused day must not stop the display.
    """
    problems = run(today)
    for problem in problems:
        print(problem)
    return not problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch, summarise and show the daily weather report.",
    )
    parser.add_argument(
        "day",
        nargs="?",
        type=date.fromisoformat,
        help="ISO date to show, e.g. 2026-10-03. Default: today.",
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

    produce(today)
    render_report(args.day or today)

    # Always 0, unlike the nightly job: a partial day is information here, not
    # failure. scripts/fetch_forecast.py stays the thing a scheduler calls.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
