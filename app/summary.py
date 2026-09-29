from app import db


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


if __name__ == "__main__":
    import json
    from datetime import datetime, timedelta, timezone

    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    print(json.dumps(build_context(tomorrow), indent=2, default=str))
