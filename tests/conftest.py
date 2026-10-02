"""Shared fixtures.

Two rules this suite keeps to:

1. No network. Nothing here calls Met Eireann, Wikipedia or the language model.

2. Writes happen against the real development database, because db.py opens a
   connection per call and so cannot be wrapped in an outer transaction.
   Tests that write use a sentinel date real data will never occupy, and delete it
   before and after.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE_XML = ROOT / "data" / "sample_forecast.xml"

# The saved forecast covers 24 Sept - 4 Oct 2026. These two days are fully
# hourly; days further out drop to 3- and 6-hourly readings.
FULL_DAY = date(2026, 9, 25)
DISTANT_DAY = date(2026, 10, 3)

# Far outside any real data, so write tests cannot collide with the app.
TEST_DAY = date(1900, 1, 1)
NEVER_SAVED_DAY = date(1900, 1, 2)


@pytest.fixture(scope="session")
def parsed_sample():
    """The saved forecast XML, parsed once for the whole run."""
    from app.forecast import parse_forecast

    return parse_forecast(SAMPLE_XML.read_text(encoding="utf-8"))


@pytest.fixture
def test_day():
    """Yield a date with no rows, and leave none behind."""
    from app.db import get_connection

    def wipe():
        with get_connection() as conn:
            conn.execute("DELETE FROM daily_summary WHERE date = %(d)s", {"d": TEST_DAY})
            conn.execute("DELETE FROM daily_forecast WHERE date = %(d)s", {"d": TEST_DAY})

    wipe()
    yield TEST_DAY
    wipe()


@pytest.fixture
def a_forecast():
    """A forecast row for TEST_DAY, in the shape summarise_day returns."""
    return {
        "date": TEST_DAY,
        "max_temp": 10.0,
        "min_temp": 5.0,
        "rain_mm": 1.0,
        "wind_speed_kt": 8.0,
        "max_gust_kt": 20.0,
        "hours": 24,
    }
