"""Fetch real historical events for a calendar date.

Events come from byabbe.se, a keyless wrapper over Wikipedia's on-this-day
data. The point is the same as with the forecast: the model is only ever handed
real facts. It picks one and phrases it - it never supplies the fact itself.
"""

import httpx

EVENTS_URL = "https://byabbe.se/on-this-day/{month}/{day}/events.json"
TIMEOUT_SECONDS = 20


def fetch_events(day):
    """Return [{"year": ..., "text": ...}] for `day`'s month and date.

    Returns an empty list if the service is unavailable. A missing fact is an
    ordinary outcome, not an error - the weather summary stands on its own.
    """
    url = EVENTS_URL.format(month=day.month, day=day.day)

    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "WexWeather/0.1"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        events = response.json().get("events", [])
    except Exception as error:
        print(f"No on-this-day events: {type(error).__name__}")
        return []

    return [
        {"year": event["year"], "text": event["description"]}
        for event in events
        if event.get("year") and event.get("description")
    ]


def render_events(events):
    """Render events as the plain text block the model chooses from."""
    return "\n".join(f"- {event['year']}: {event['text']}" for event in events)


if __name__ == "__main__":
    from datetime import date

    events = fetch_events(date.today())
    print(f"{len(events)} events")
    print(render_events(events[:5]))
