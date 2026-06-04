"""Integration and unit tests for the recommendation orchestration pipeline (Phase 4)."""

from __future__ import annotations

import pytest

from src.filtering.candidate_filter import FilterResult
from src.llm.client import FakeLLMClient, LLMTimeoutError
from src.llm.response_parser import LLMParseError
from src.models.preferences import Budget, UserPreferences
from src.models.recommendation import RecommendationResponse
from src.models.restaurant import Restaurant
from src.orchestration.recommender import RecommenderService


@pytest.fixture
def mock_restaurants():
    return [
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


class MockStore:
    def __init__(self, restaurants):
        self.restaurants = restaurants

    def get_all(self):
        return self.restaurants


def test_recommender_happy_path(mock_restaurants):
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="nice ambiance",
    )

    store = MockStore(mock_restaurants)
    
    # Fake LLM response with valid JSON structure
    fake_json = """
    {
        "summary": "Top Italian picks in Bangalore.",
        "recommendations": [
            {"id": "rest-1", "rank": 1, "explanation": "Excellent fine dining Toscano."},
            {"id": "rest-2", "rank": 2, "explanation": "Great Koramangala Chianti."}
        ]
    }
    """
    llm_client = FakeLLMClient(response_text=fake_json)

    service = RecommenderService(store=store, llm_client=llm_client)
    res = service.recommend(prefs)

    assert isinstance(res, RecommendationResponse)
    assert res.status == "success"
    assert res.summary == "Top Italian picks in Bangalore."
    assert len(res.recommendations) == 2
    assert res.recommendations[0].restaurant.id == "rest-1"
    assert res.recommendations[0].rank == 1
    assert res.recommendations[0].explanation == "Excellent fine dining Toscano."
    assert res.recommendations[1].restaurant.id == "rest-2"
    assert res.recommendations[1].rank == 2

    # Check metadata enrichment
    assert res.metadata["llm_called"] is True
    assert "llm_latency_ms" in res.metadata
    assert res.metadata["candidates_considered"] == 2
    assert res.metadata["filters_applied"]["location"] == "Bangalore"
    assert res.metadata["filters_applied"]["budget"] == "medium"


def test_recommender_empty_candidates(mock_restaurants):
    # Min rating of 5.0 on these mock restaurants will produce empty candidates
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=5.0,
    )

    store = MockStore(mock_restaurants)
    # The client shouldn't even be called
    llm_client = FakeLLMClient(should_raise=Exception("Should not be called!"))

    service = RecommenderService(store=store, llm_client=llm_client)
    res = service.recommend(prefs)

    assert isinstance(res, RecommendationResponse)
    assert res.status == "empty"
    assert len(res.recommendations) == 0
    assert "No restaurants found" in res.message
    assert res.metadata["llm_called"] is False
    assert res.metadata["candidates_considered"] == 2


def test_recommender_llm_timeout(mock_restaurants):
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )

    store = MockStore(mock_restaurants)
    # Setup LLM client to raise timeout error
    llm_client = FakeLLMClient(should_raise=LLMTimeoutError("API timed out"))

    service = RecommenderService(store=store, llm_client=llm_client)
    res = service.recommend(prefs)

    assert isinstance(res, RecommendationResponse)
    assert res.status == "error"
    assert "temporarily unavailable" in res.message
    assert res.metadata["llm_called"] is True
    assert res.metadata["error_type"] == "LLMTimeoutError"


def test_recommender_llm_parse_failure(mock_restaurants):
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )

    store = MockStore(mock_restaurants)
    # Parser should raise LLMParseError for malformed JSON
    llm_client = FakeLLMClient(response_text="{ malformed json }")

    service = RecommenderService(store=store, llm_client=llm_client)
    res = service.recommend(prefs)

    assert isinstance(res, RecommendationResponse)
    assert res.status == "error"
    assert "couldn't generate recommendations" in res.message
    assert res.metadata["llm_called"] is True
    assert res.metadata["error_type"] == "LLMParseError"
