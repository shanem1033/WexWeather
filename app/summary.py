from google import genai

from app import db, onthisday

# db.py calls load_dotenv() on import, so GEMINI_API_KEY is already in the
# environment by the time genai.Client() looks for it.

# A lite model is plenty: it is handed the facts and only has to phrase them.
# Free-tier quota is per model and small (20 requests/day), so the lighter
# model also keeps the heavier one in reserve.
SUMMARY_MODEL = "gemini-3.5-flash-lite"

# The SDK retries 408/429/5xx itself, with exponential backoff - by default 5
# attempts starting at 1s and doubling. Wrapping that in our own retry loop
# would multiply the two (3 x 5 = 15 requests per summary) and burn the free
# tier's quota, so we configure the SDK's retries instead of adding our own.
#
# timeout is per request, in milliseconds. Without it the SDK waits
# indefinitely, and a nightly job that hangs is worse than one that fails: no
# output and no error either.
HTTP_OPTIONS = {
    "timeout": 20_000,
    "retry_options": {"attempts": 3, "initial_delay": 2.0, "max_delay": 20.0},
}

PROMPT = """You are writing one short sentence for a local weather page for Wexford, Ireland.

Below are real, pre-computed numbers about a single day's forecast and how it
compares with the same calendar date in previous years.

{facts}

Use ONLY the numbers above. Do not estimate, infer, or mention any weather
detail that is not listed. Write one sentence of at most 25 words highlighting
whatever is most notable. If nothing stands out - everything mid-table - say
that plainly rather than inventing significance. No exclamation marks."""

ON_THIS_DAY_PROMPT = """Below are real historical events that happened on this
calendar date, taken from Wikipedia.

{events}

Pick ONE event that is positive or uplifting - an achievement, a discovery, a
founding, a first, a peaceful milestone. Avoid wars, disasters, deaths, attacks
and crises.

Use ONLY the events listed above. Do not add detail that is not in the entry
you pick. Write one sentence of at most 25 words, starting with the year. If
none of the events are positive, reply exactly: Nothing especially cheerful
happened on this date."""


# Which forecast fields are worth comparing against history, and which end of
# the range is the interesting one. "high" means rank 1 is the largest value
# (hottest, wettest, windiest); "low" means rank 1 is the smallest (coldest).
COMPARE_FIELDS = [
    ("max_temp", "high"),
    ("min_temp", "low"),
    ("rain_mm", "high"),
    ("max_gust_kt", "high"),
]


def rank_against_history(value, rows, field, direction="high"):
    if direction not in ("high", "low"):
        raise ValueError(f"direction must be 'high' or 'low', got {direction!r}")

    if value is None:
        return None

    usable = [row for row in rows if row[field] is not None]
    if not usable:
        return None

    values = [row[field] for row in usable]

    if direction == "high":
        beaten_by = sum(1 for other in values if other > value)
        record = max(values)
    else:
        beaten_by = sum(1 for other in values if other < value)
        record = min(values)

    record_year = usable[values.index(record)]["date"].year

    return {
        "field": field,
        "direction": direction,
        "value": value,
        "rank": beaten_by + 1,
        "of": len(usable) + 1,
        "record": record,
        "record_year": record_year,
    }


def build_context(day):
    forecast = db.get_forecast(day)
    if forecast is None:
        return None

    rows = db.get_history_for_day(day.month, day.day)

    comparisons = []
    for field, direction in COMPARE_FIELDS:
        comparison = rank_against_history(forecast[field], rows, field, direction)
        if comparison is not None:
            comparisons.append(comparison)

    return {
        "date": day,
        "forecast": forecast,
        "history": db.get_day_stats(day.month, day.day),
        "comparisons": comparisons,
    }


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


LABELS = {
    "max_temp": ("Highest temperature", "C"),
    "min_temp": ("Lowest temperature", "C"),
    "rain_mm": ("Rainfall", "mm"),
    "max_gust_kt": ("Highest gust", "kt"),
}


def render_facts(context):
    """Turn a context dict into the plain text block the model reads.

    This is the only place numbers get rounded - everything upstream keeps
    full precision.
    """
    day = context["date"]
    forecast = context["forecast"]
    history = context["history"]

    lines = [
        f"Date: {day.day} {day:%B %Y}",
        f"Forecast: max {forecast['max_temp']:.1f}C, min {forecast['min_temp']:.1f}C, "
        f"rain {forecast['rain_mm']:.1f}mm, mean wind {forecast['wind_speed_kt']:.0f}kt, "
        f"gust {forecast['max_gust_kt']:.0f}kt",
        f"History for this date: {history['years']} previous years, "
        f"average max {history['avg_max_temp']}C, average rain {history['avg_rain_mm']}mm",
        "",
        "How the forecast ranks against those years:",
    ]

    for c in context["comparisons"]:
        label, unit = LABELS[c["field"]]
        end = "highest" if c["direction"] == "high" else "lowest"
        lines.append(
            f"- {label} {c['value']:.1f}{unit} is the {_ordinal(c['rank'])} {end} "
            f"of {c['of']} (previous record {c['record']:.1f}{unit} in {c['record_year']})"
        )

    return "\n".join(lines)


def summarise(context, model=SUMMARY_MODEL):
    """Ask the model for one sentence about `context`.

    Returns None if the model is unavailable. A missing summary is an ordinary
    outcome - the forecast is already saved and the API still serves stats, so
    a bad night costs a sentence, not the pipeline.
    """
    if context is None:
        return None
    return _ask(PROMPT.format(facts=render_facts(context)), model, "weather summary")


def summarise_on_this_day(events, model=SUMMARY_MODEL):
    """Pick one positive historical event from `events` and phrase it.

    `events` comes from onthisday.fetch_events(). Returns None if there are no
    events or the model is unavailable.
    """
    if not events:
        return None

    prompt = ON_THIS_DAY_PROMPT.format(events=onthisday.render_events(events))
    return _ask(prompt, model, "on-this-day fact")


def _ask(prompt, model, label):
    """Send one prompt and return the text, or None if the model is unavailable.

    Both summaries need the same behaviour: a bounded request, a few retries
    for the transient 503s the free tier throws, and never raising - a bad
    night costs a sentence, not the pipeline.
    """
    client = genai.Client(http_options=HTTP_OPTIONS)

    try:
        response = client.interactions.create(model=model, input=prompt)
        return response.output_text.strip()
    except Exception as error:
        # The message matters: a per-minute limit means try later tonight, a
        # daily one means not today. Type alone does not distinguish them.
        print(f"No {label}: {type(error).__name__} - {str(error)[:200]}")
        return None


if __name__ == "__main__":
    import sys
    from datetime import date, datetime, timedelta, timezone

    if len(sys.argv) > 1:
        day = date.fromisoformat(sys.argv[1])
    else:
        day = datetime.now(timezone.utc).date() + timedelta(days=1)

    context = build_context(day)
    if context is None:
        print(f"No forecast saved for {day}")
    else:
        print(render_facts(context))
        print()
        print("WEATHER:", summarise(context))

    print("ON THIS DAY:", summarise_on_this_day(onthisday.fetch_events(day)))
