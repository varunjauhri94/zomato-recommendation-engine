"""Unit tests for candidate filtering."""

from __future__ import annotations

import time

import pytest

from src.filtering.candidate_filter import filter_restaurants
from src.models.preferences import Budget, UserPreferences
from src.models.restaurant import Restaurant

FIXTURES = [
    Restaurant(
        id="1",
        name="Alpha Italian",
        location="Indiranagar",
        city="Bangalore",
        cuisine="italian, pizza",
        rating=4.5,
        cost_for_two=900,
        budget_band="medium",
    ),
    Restaurant(
        id="2",
        name="Beta Chinese",
        location="Koramangala",
        city="Bangalore",
        cuisine="chinese",
        rating=4.0,
        cost_for_two=400,
        budget_band="low",
    ),
    Restaurant(
        id="3",
        name="Gamma Italian Budget",
        location="Jayanagar",
        city="Bangalore",
        cuisine="italian",
        rating=3.5,
        cost_for_two=300,
        budget_band="low",
    ),
    Restaurant(
        id="4",
        name="Delta Fine",
        location="CP",
        city="Delhi",
        cuisine="italian",
        rating=4.8,
        cost_for_two=2000,
        budget_band="high",
    ),
    Restaurant(
        id="5",
        name="Echo New",
        location="HSR",
        city="Bangalore",
        cuisine="italian",
        rating=None,
        cost_for_two=600,
        budget_band="medium",
    ),
    Restaurant(
        id="6",
        name="Fox Unknown Cost",
        location="BTM",
        city="Bangalore",
        cuisine="italian",
        rating=4.2,
        cost_for_two=None,
        budget_band="unknown",
    ),
]


def test_filter_location_case_insensitive():
    prefs = UserPreferences(
        location="bengaluru",
        budget=Budget.MEDIUM,
        cuisine="any",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert len(result.candidates) >= 2
    assert all(r.city == "Bangalore" for r in result.candidates)
    assert all(r.budget_band == "medium" for r in result.candidates)


def test_filter_cuisine_substring():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    names = {r.name for r in result.candidates}
    assert "Alpha Italian" in names
    assert "Beta Chinese" not in names


def test_filter_cuisine_any_skips_cuisine():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.LOW,
        cuisine="*",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert any(r.name == "Beta Chinese" for r in result.candidates)


def test_filter_min_rating_excludes_null_and_low():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    names = {r.name for r in result.candidates}
    assert "Alpha Italian" in names
    assert "Echo New" not in names
    assert "Gamma Italian Budget" not in names


def test_filter_budget_excludes_unknown_band():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    names = {r.name for r in result.candidates}
    assert "Fox Unknown Cost" not in names


def test_filter_budget_low():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.LOW,
        cuisine="any",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert all(r.budget_band == "low" for r in result.candidates)


def test_filter_empty_impossible_rating():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=5.0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert result.is_empty
    assert result.message is not None


def test_filter_empty_unknown_city():
    prefs = UserPreferences(
        location="Mumbai",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert result.is_empty
    assert "Mumbai" in result.message or "No restaurants" in result.message


def test_filter_top_n_cap():
    many = [
        Restaurant(
            id=str(i),
            name=f"R{i}",
            location="X",
            city="Bangalore",
            cuisine="italian",
            rating=3.0 + i * 0.01,
            cost_for_two=800,
            budget_band="medium",
        )
        for i in range(50)
    ]
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=0,
    )
    result = filter_restaurants(many, prefs, top_n=10)
    assert len(result.candidates) == 10
    ratings = [r.rating for r in result.candidates]
    assert ratings == sorted(ratings, reverse=True)


def test_filter_tiebreaker_stable_by_name():
    tied = [
        Restaurant(
            id="b",
            name="Bravo",
            location="A",
            city="Bangalore",
            cuisine="italian",
            rating=4.0,
            cost_for_two=800,
            budget_band="medium",
        ),
        Restaurant(
            id="a",
            name="Alpha",
            location="B",
            city="Bangalore",
            cuisine="italian",
            rating=4.0,
            cost_for_two=800,
            budget_band="medium",
        ),
    ]
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=0,
    )
    result = filter_restaurants(tied, prefs)
    assert result.candidates[0].name == "Alpha"


def test_filter_empty_store_list():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=0,
    )
    result = filter_restaurants([], prefs)
    assert result.is_empty
    assert "not loaded" in result.message.lower()


def test_filter_metadata_populated():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    result = filter_restaurants(FIXTURES, prefs)
    assert result.metadata["filters_applied"]["location"] == "Bangalore"
    assert result.metadata["filters_applied"]["budget"] == "medium"
    assert result.metadata["llm_called"] is False


def test_user_preferences_validation():
    with pytest.raises(Exception):
        UserPreferences(location="", budget=Budget.LOW, cuisine="Italian", min_rating=0)
    with pytest.raises(Exception):
        UserPreferences(location="Bangalore", budget=Budget.LOW, cuisine="", min_rating=0)
    with pytest.raises(Exception):
        UserPreferences(
            location="Bangalore",
            budget=Budget.LOW,
            cuisine="Italian",
            min_rating=6.0,
        )


def test_user_preferences_additional_whitespace():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.LOW,
        cuisine="Italian",
        additional_preferences="   ",
    )
    assert prefs.additional_preferences is None


def test_filter_performance_under_50ms():
    """Architecture latency target on in-memory list."""
    large = [
        Restaurant(
            id=str(i),
            name=f"Place {i}",
            location="Loc",
            city="Bangalore",
            cuisine="north indian, chinese",
            rating=3.5 + (i % 15) * 0.1,
            cost_for_two=500 + (i % 3) * 400,
            budget_band=["low", "medium", "high"][i % 3],
        )
        for i in range(12_000)
    ]
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="indian",
        min_rating=3.5,
    )
    start = time.perf_counter()
    result = filter_restaurants(large, prefs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f"filter took {elapsed_ms:.1f}ms"
    assert len(result.candidates) <= 30
