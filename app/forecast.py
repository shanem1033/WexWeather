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
            wind = loc.find("windSpeed")
            gust = loc.find("windGust")
            instants.append({
                "time": start,
                "temp": float(loc.find("temperature").get("value")),
                "wind_kt": float(wind.get("mps")) * MPS_TO_KT,
                "gust_kt": float(gust.get("mps")) * MPS_TO_KT if gust is not None else None,
            })
        else:
            rain.append({
                "start": start,
                "end": end,
                "rain_mm": float(loc.find("precipitation").get("value")),
            })

    return instants, rain


def summarise_day(instants, rain, day):
    """Summarise one UTC day of forecast data in the same shape as daily_weather."""
    day_instants = [e for e in instants if e["time"].date() == day]
    day_rain = [e for e in rain if e["start"].date() == day]

    temps = [e["temp"] for e in day_instants]
    winds = [e["wind_kt"] for e in day_instants]
    gusts = [e["gust_kt"] for e in day_instants if e["gust_kt"] is not None]

    return {
        "date": day,
        "hours": len(day_instants),
        "max_temp": max(temps) if temps else None,
        "min_temp": min(temps) if temps else None,
        "rain_mm": sum(e["rain_mm"] for e in day_rain) if day_rain else None,
        "wind_speed_kt": sum(winds) / len(winds) if winds else None,
        "max_gust_kt": max(gusts) if gusts else None,
    }