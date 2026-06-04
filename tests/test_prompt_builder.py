"""Unit tests for the prompt builder."""

from __future__ import annotations

import json
from src.llm.prompt_builder import build_recommendation_prompt
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant


def test_build_recommendation_prompt_basic():
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="quiet place, outdoor seating",
    )

    candidates = [
        Restaurant(
            id="rest-1",
            name="Toscano",
            location="UB City",
            city="Bangalore",
            cuisine="Italian",
            rating=4.5,
            cost_for_two=1200,
            budget_band="medium",
            raw={"some_field": "some_value"},
        ),
        Restaurant(
            id="rest-2",
            name="Chianti",
            location="Koramangala",
            city="Bangalore",
            cuisine="Italian",
            rating=4.3,
            cost_for_two=1400,
            budget_band="medium",
            raw={"some_field2": "some_value2"},
        ),
    ]

    system, user = build_recommendation_prompt(prefs, candidates, top_k=5)

    assert "expert restaurant recommendation engine" in system
    assert "strict rules" in system
    assert "JSON schema" in system

    user_data = json.loads(user)
    assert user_data["preferences"]["location"] == "Bangalore"
    assert user_data["preferences"]["budget"] == "medium"
    assert user_data["preferences"]["cuisine"] == "Italian"
    assert user_data["preferences"]["additional_preferences"] == "quiet place, outdoor seating"
    assert user_data["request_top_k"] == 2  # min(5, len(candidates))

    assert len(user_data["candidates"]) == 2
    assert user_data["candidates"][0]["id"] == "rest-1"
    assert user_data["candidates"][0]["name"] == "Toscano"
    assert "raw" not in user_data["candidates"][0]  # raw dictionary must be omitted


def test_build_recommendation_prompt_no_additional_preferences():
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences=None,
    )

    candidates = [
        Restaurant(
            id="rest-1",
            name="Toscano",
            location="UB City",
            city="Bangalore",
            cuisine="Italian",
            rating=4.5,
            cost_for_two=1200,
            budget_band="medium",
        )
    ]

    _, user = build_recommendation_prompt(prefs, candidates, top_k=5)
    user_data = json.loads(user)

    assert "additional_preferences" not in user_data["preferences"]


def test_build_recommendation_prompt_top_k_limiting():
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
    )

    candidates = [
        Restaurant(
            id="rest-1",
            name="Toscano",
            location="UB City",
            city="Bangalore",
            cuisine="Italian",
            rating=4.5,
            cost_for_two=1200,
            budget_band="medium",
        ),
        Restaurant(
            id="rest-2",
            name="Chianti",
            location="Koramangala",
            city="Bangalore",
            cuisine="Italian",
            rating=4.3,
            cost_for_two=1400,
            budget_band="medium",
        ),
    ]

    _, user = build_recommendation_prompt(prefs, candidates, top_k=1)
    user_data = json.loads(user)
    assert user_data["request_top_k"] == 1
