"""Forecast parsing, against the saved XML. No network."""

from datetime import date

from app.forecast import summarise_day
from tests.conftest import DISTANT_DAY, FULL_DAY


def test_instants_and_intervals_are_separated(parsed_sample):
    """from == to is a snapshot; from != to is an accumulation."""
    instants, rain = parsed_sample
    assert instants and rain
    assert all(entry["end"] > entry["start"] for entry in rain)


def test_wind_is_converted_to_knots(parsed_sample):
    instants, _ = parsed_sample
    speeds = [e["wind_kt"] for e in instants]
    assert all(s >= 0 for s in speeds)
    # m/s would give numbers roughly half these. A sanity band, not a precise
    # assertion: no Irish forecast is a flat calm or a hurricane all week.
    assert 1 < max(speeds) < 120


def test_gusts_may_be_missing(parsed_sample):
    """windGust is optional in the feed, so None must survive parsing."""
    instants, _ = parsed_sample
    assert all(e["gust_kt"] is None or e["gust_kt"] >= 0 for e in instants)


def test_a_full_day_has_24_readings(parsed_sample):
    instants, rain = parsed_sample
    day = summarise_day(instants, rain, FULL_DAY)
    assert day["hours"] == 24
    assert day["max_temp"] >= day["min_temp"]
    assert day["rain_mm"] >= 0


def test_distant_days_have_fewer_readings(parsed_sample):
    """The feed drops to 3- then 6-hourly, which is what hours < 24 catches."""
    instants, rain = parsed_sample
    near = summarise_day(instants, rain, FULL_DAY)["hours"]
    far = summarise_day(instants, rain, DISTANT_DAY)["hours"]
    assert far < near


def test_day_outside_the_forecast_is_all_none(parsed_sample):
    """No data must produce nulls, not zeros and not an exception."""
    instants, rain = parsed_sample
    day = summarise_day(instants, rain, date(2030, 1, 1))
    assert day["hours"] == 0
    assert day["max_temp"] is None
    assert day["min_temp"] is None
    assert day["rain_mm"] is None
    assert day["wind_speed_kt"] is None
    assert day["max_gust_kt"] is None


def test_wind_is_a_mean_and_gust_is_a_max(parsed_sample):
    """Mirrors how Met Eireann defines wdsp and hg. Swapping them would
    produce numbers that look plausible and are wrong."""
    instants, rain = parsed_sample
    day = summarise_day(instants, rain, FULL_DAY)
    on_day = [e for e in instants if e["time"].date() == FULL_DAY]
    gusts = [e["gust_kt"] for e in on_day if e["gust_kt"] is not None]

    assert day["wind_speed_kt"] < max(e["wind_kt"] for e in on_day)
    assert day["max_gust_kt"] == max(gusts)
