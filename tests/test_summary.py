"""Ranking and fact rendering. Pure functions - no database, no network."""

from datetime import date

import pytest

from app.summary import _ordinal, rank_against_history, render_facts, summarise


def years(*pairs):
    """Build history rows: years((2020, 15.0), (2021, 18.4))"""
    return [{"date": date(y, 9, 29), "max_temp": v} for y, v in pairs]


def test_rank_one_is_the_highest_when_direction_is_high():
    result = rank_against_history(20.0, years((2020, 15.0), (2021, 18.4)), "max_temp", "high")
    assert result["rank"] == 1
    assert result["record"] == 18.4
    assert result["record_year"] == 2021


def test_rank_one_is_the_lowest_when_direction_is_low():
    result = rank_against_history(1.0, years((2020, 15.0), (2021, 18.4)), "max_temp", "low")
    assert result["rank"] == 1
    assert result["record"] == 15.0
    assert result["record_year"] == 2020


def test_of_counts_the_forecast_alongside_the_years():
    """Regression: a record-breaking value once reported 'rank 11 of 10'."""
    result = rank_against_history(99.0, years((2020, 1.0), (2021, 2.0)), "max_temp", "high")
    assert result["of"] == 3
    assert 1 <= result["rank"] <= result["of"]


def test_rank_never_exceeds_of_at_either_extreme():
    data = years((2020, 10.0), (2021, 20.0), (2022, 30.0))
    for value in (-100.0, 0.0, 15.0, 100.0):
        for direction in ("high", "low"):
            result = rank_against_history(value, data, "max_temp", direction)
            assert 1 <= result["rank"] <= result["of"]


def test_nulls_are_skipped_and_do_not_inflate_the_count():
    data = years((2020, 15.0)) + [{"date": date(2021, 9, 29), "max_temp": None}]
    result = rank_against_history(17.0, data, "max_temp", "high")
    assert result["of"] == 2  # one usable year plus the forecast


def test_ties_share_a_rank_and_credit_the_earliest_year():
    result = rank_against_history(18.4, years((2019, 18.4), (2021, 18.4)), "max_temp", "high")
    assert result["rank"] == 1
    assert result["record_year"] == 2019


def test_missing_value_returns_none():
    assert rank_against_history(None, years((2020, 15.0)), "max_temp") is None


def test_no_usable_history_returns_none():
    assert rank_against_history(17.0, [], "max_temp") is None
    only_nulls = [{"date": date(2020, 9, 29), "max_temp": None}]
    assert rank_against_history(17.0, only_nulls, "max_temp") is None


def test_unknown_direction_raises():
    with pytest.raises(ValueError):
        rank_against_history(17.0, years((2020, 15.0)), "max_temp", "sideways")


@pytest.mark.parametrize(
    "number,expected",
    [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"),
     (11, "11th"), (12, "12th"), (13, "13th"), (21, "21st"), (22, "22nd")],
)
def test_ordinals(number, expected):
    assert _ordinal(number) == expected


def test_render_facts_rounds_only_for_display():
    context = {
        "date": date(2026, 9, 29),
        "forecast": {
            "max_temp": 17.1, "min_temp": 11.4, "rain_mm": 9.1,
            "wind_speed_kt": 15.494024, "max_gust_kt": 41.986942,
        },
        "history": {"years": 10, "avg_max_temp": "15.4", "avg_rain_mm": "3.9"},
        "comparisons": [{
            "field": "max_gust_kt", "direction": "high", "value": 41.986942,
            "rank": 1, "of": 11, "record": 39.0, "record_year": 2024,
        }],
    }
    text = render_facts(context)

    assert "42kt" in text
    assert "41.986942" not in text
    assert "1st highest of 11" in text
    assert "2024" in text


def test_summarise_without_a_context_makes_no_request():
    """Short-circuits before touching the network, so this is safe to run."""
    assert summarise(None) is None
