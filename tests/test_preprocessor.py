"""Unit tests for data preprocessing."""

from __future__ import annotations

from src.config import Settings
from src.data.preprocessor import (
    extract_city_from_address,
    parse_cost,
    parse_rating,
    preprocess_records,
    preprocess_row,
)
from src.data.preprocessor import PreprocessStats


def test_parse_rating_valid():
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("4.0/5") == 4.0


def test_parse_rating_invalid():
    assert parse_rating("NEW") is None
    assert parse_rating(None) is None
    assert parse_rating("") is None


def test_parse_cost_with_comma():
    assert parse_cost("1,200") == 1200
    assert parse_cost("800") == 800
    assert parse_cost("-") is None


def test_extract_city_bangalore():
    addr = "942, 21st Main Road, Banashankari, Bangalore"
    assert extract_city_from_address(addr) == "Bangalore"


def test_extract_city_bengaluru_alias():
    addr = "Jayanagar, Bengaluru"
    assert extract_city_from_address(addr) == "Bangalore"


def test_extract_city_defaults_none():
    assert extract_city_from_address("Some local road, Banashankari") is None


def test_budget_band_mapping():
    settings = Settings(budget_low_max=500, budget_medium_max=1500)
    assert settings.cost_to_budget_band(400) == "low"
    assert settings.cost_to_budget_band(500) == "low"
    assert settings.cost_to_budget_band(501) == "medium"
    assert settings.cost_to_budget_band(1500) == "medium"
    assert settings.cost_to_budget_band(1501) == "high"
    assert settings.cost_to_budget_band(None) == "unknown"


def test_preprocess_row_minimal():
    stats = PreprocessStats()
    row = {
        "name": "Test Cafe",
        "address": "Banashankari, Bangalore",
        "location": "Banashankari",
        "cuisines": "Italian, Pizza",
        "rate": "4.2/5",
        "approx_cost(for two people)": "800",
    }
    restaurant = preprocess_row(row, 0, stats)
    assert restaurant is not None
    assert restaurant.name == "Test Cafe"
    assert restaurant.city == "Bangalore"
    assert restaurant.cuisine == "italian, pizza"
    assert restaurant.rating == 4.2
    assert restaurant.cost_for_two == 800
    assert restaurant.budget_band == "medium"


def test_preprocess_row_drops_missing_name():
    stats = PreprocessStats()
    row = {"name": "", "address": "Bangalore", "cuisines": "Italian", "rate": "4.0/5"}
    assert preprocess_row(row, 0, stats) is None
    assert stats.dropped_missing_name == 1


def test_preprocess_records_dedupes_by_name_city():
    records = [
        {
            "name": "Jalsa",
            "address": "Banashankari, Bangalore",
            "location": "Banashankari",
            "cuisines": "North Indian",
            "rate": "4.0/5",
            "approx_cost(for two people)": "600",
        },
        {
            "name": "Jalsa",
            "address": "Banashankari, Bangalore",
            "location": "Banashankari",
            "cuisines": "North Indian",
            "rate": "4.5/5",
            "approx_cost(for two people)": "700",
        },
    ]
    restaurants, stats = preprocess_records(records)
    assert len(restaurants) == 1
    assert restaurants[0].rating == 4.5
    assert stats.collapsed_duplicates == 1


def test_preprocess_records_keeps_new_rating_rows():
    records = [
        {
            "name": "New Place",
            "address": "Koramangala, Bangalore",
            "location": "Koramangala",
            "cuisines": "Cafe",
            "rate": "NEW",
            "approx_cost(for two people)": "300",
        }
    ]
    restaurants, _ = preprocess_records(records)
    assert len(restaurants) == 1
    assert restaurants[0].rating is None


def test_normalize_location_aliases():
    settings = Settings()
    assert settings.normalize_location("bengaluru") == "Bangalore"
    assert settings.normalize_location("new delhi") == "Delhi"
