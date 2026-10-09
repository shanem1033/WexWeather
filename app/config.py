"""Settings shared across the app, loaded once.

Secrets come from environment variables. Locally, load_dotenv() fills them in
from .env; on a server the host sets them and there is no .env, so
load_dotenv() quietly does nothing.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# Optional: only the summaries need it, so a missing key must not stop the
# rest of the app from starting.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Johnstown Castle II, Co. Wexford: the one station the app covers.
STATION = {
    "station_id": 1775,
    "name": "Johnstown Castle II",
    "county": "Wexford",
    "latitude": 52.298,
    "longitude": -6.497,
}
STATION_ID = STATION["station_id"]
