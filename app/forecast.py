# This file contains the functions for fetching forcast, parsing into lists and finally building one dict of the forecaast that matches the historic weather data format
import xml.etree.ElementTree as ET
from datetime import datetime
import httpx

FORECAST_URL = "http://openaccess.pf.api.met.ie/metno-wdb2ts/locationforecast"

MPS_TO_KT = 1.94384


def fetch_forecast_xml(lat, lon):
    """Download the raw forecast XML for a point."""
    response = httpx.get(f"{FORECAST_URL}?lat={lat};long={lon}", timeout=30)
    response.raise_for_status()
    return response.text


def parse_forecast(xml_text):
    """Split the forecast into instant readings and rain intervals."""
    root = ET.fromstring(xml_text)
    instants = []
    rain = []

    for time in root.iter("time"):
        start = datetime.fromisoformat(time.get("from"))
        end = datetime.fromisoformat(time.get("to"))
        loc = time.find("location")

        if start == end:
            instants.append({
                "time": start,
                "temp": _read_value(loc, "temperature", "value"),
                "wind_kt": _read_value(loc, "windSpeed", "mps", MPS_TO_KT),
                "gust_kt": _read_value(loc, "windGust", "mps", MPS_TO_KT),
            })
        else:
            rain.append({
                "start": start,
                "end": end,
                "rain_mm": _read_value(loc, "precipitation", "value"),
            })

    return instants, rain


def _read_value(loc, tag, attribute, scale=1.0):
    """Read one number from a <location>, or None if the feed left it out.

    Any element can be missing from a given hour, so None here is the same
    "no reading" that NULL means in the database.
    """
    element = loc.find(tag)
    if element is None or element.get(attribute) is None:
        return None
    return float(element.get(attribute)) * scale


def summarise_day(instants, rain, day):
    """Summarise one UTC day of forecast data in the same shape as daily_weather.

    Missing readings are skipped, so a field is None only when the day has no
    readings for it at all.
    """
    day_instants = [e for e in instants if e["time"].date() == day]
    day_rain = [e for e in rain if e["start"].date() == day]

    temps = [e["temp"] for e in day_instants if e["temp"] is not None]
    winds = [e["wind_kt"] for e in day_instants if e["wind_kt"] is not None]
    gusts = [e["gust_kt"] for e in day_instants if e["gust_kt"] is not None]
    rains = [e["rain_mm"] for e in day_rain if e["rain_mm"] is not None]

    return {
        "date": day,
        "hours": len(day_instants),
        "max_temp": max(temps) if temps else None,
        "min_temp": min(temps) if temps else None,
        "rain_mm": sum(rains) if rains else None,
        "wind_speed_kt": sum(winds) / len(winds) if winds else None,
        "max_gust_kt": max(gusts) if gusts else None,
    }
