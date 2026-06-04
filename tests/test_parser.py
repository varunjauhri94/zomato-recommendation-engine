"""Unit tests for the response parser."""

from __future__ import annotations

import pytest

from src.llm.response_parser import parse_llm_response, LLMParseError
from src.models.restaurant import Restaurant


@pytest.fixture
def candidates():
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
        Restaurant(
            id="rest-3",
            name="Glen's Bakehouse",
            location="Indiranagar",
            city="Bangalore",
            cuisine="Italian, Cafe",
            rating=4.0,
            cost_for_two=600,
            budget_band="medium",
        ),
    ]


def test_parse_llm_response_happy_path(candidates):
    raw_response = """
    {
        "summary": "Three great Italian places.",
        "recommendations": [
            {"id": "rest-2", "rank": 2, "explanation": "Excellent ambiance and pasta."},
            {"id": "rest-1", "rank": 1, "explanation": "Highly rated fine dining."}
        ]
    }
    """

    res = parse_llm_response(raw_response, candidates)

    assert res.status == "success"
    assert res.summary == "Three great Italian places."
    assert len(res.recommendations) == 2
    assert not res.warnings

    # Verify sorting and sequential re-ranking
    # rest-1 had rank 1, rest-2 had rank 2. They should be ordered: rest-1 (rank 1), rest-2 (rank 2)
    assert res.recommendations[0].restaurant.id == "rest-1"
    assert res.recommendations[0].rank == 1
    assert res.recommendations[0].explanation == "Highly rated fine dining."

    assert res.recommendations[1].restaurant.id == "rest-2"
    assert res.recommendations[1].rank == 2
    assert res.recommendations[1].explanation == "Excellent ambiance and pasta."


def test_parse_llm_response_code_fences(candidates):
    raw_response = """```json
    {
        "summary": "Markdown fenced response",
        "recommendations": [
            {"id": "rest-3", "rank": 1, "explanation": "Yummy cakes"}
        ]
    }
    ```"""

    res = parse_llm_response(raw_response, candidates)
    assert res.status == "success"
    assert len(res.recommendations) == 1
    assert res.recommendations[0].restaurant.id == "rest-3"


def test_parse_llm_response_hallucinated_id(candidates):
    raw_response = """
    {
        "summary": "Includes a fake id",
        "recommendations": [
            {"id": "rest-1", "rank": 1, "explanation": "Good Toscano"},
            {"id": "fake-id", "rank": 2, "explanation": "This does not exist"}
        ]
    }
    """

    res = parse_llm_response(raw_response, candidates)
    
    assert res.status == "partial"
    assert len(res.recommendations) == 1
    assert res.recommendations[0].restaurant.id == "rest-1"
    assert "Hallucinated candidate ID 'fake-id' dropped." in res.warnings


def test_parse_llm_response_all_hallucinated_ids(candidates):
    raw_response = """
    {
        "summary": "All fake ids",
        "recommendations": [
            {"id": "fake-1", "rank": 1, "explanation": "fake"},
            {"id": "fake-2", "rank": 2, "explanation": "fake"}
        ]
    }
    """

    with pytest.raises(LLMParseError) as exc:
        parse_llm_response(raw_response, candidates)
    assert "Please try again." in str(exc.value)


def test_parse_llm_response_re_ranks_sequential(candidates):
    raw_response = """
    {
        "summary": "Non-sequential ranks in response",
        "recommendations": [
            {"id": "rest-3", "rank": 10, "explanation": "Glens"},
            {"id": "rest-1", "rank": 5, "explanation": "Toscano"}
        ]
    }
    """

    res = parse_llm_response(raw_response, candidates)

    assert res.status == "success"
    assert len(res.recommendations) == 2
    # rest-1 (rank 5) should be ranked 1, rest-3 (rank 10) should be ranked 2
    assert res.recommendations[0].restaurant.id == "rest-1"
    assert res.recommendations[0].rank == 1
    assert res.recommendations[1].restaurant.id == "rest-3"
    assert res.recommendations[1].rank == 2


def test_parse_llm_response_ground_truth_protection(candidates):
    # The LLM returns a hallucinated rating of 5.0 and cost of 2000 for rest-1
    raw_response = """
    {
        "summary": "Trying to override database values",
        "recommendations": [
            {
                "id": "rest-1", 
                "rank": 1, 
                "name": "Super Toscano",
                "rating": 5.0,
                "cost_for_two": 2000,
                "explanation": "Toscano description"
            }
        ]
    }
    """

    res = parse_llm_response(raw_response, candidates)
    
    assert len(res.recommendations) == 1
    # Check that we preserved the database record fields
    assert res.recommendations[0].restaurant.name == "Toscano"
    assert res.recommendations[0].restaurant.rating == 4.5
    assert res.recommendations[0].restaurant.cost_for_two == 1200


def test_parse_llm_response_malformed_json(candidates):
    raw_response = "{ malformed json: "

    with pytest.raises(LLMParseError) as exc:
        parse_llm_response(raw_response, candidates)
    assert "Please try again." in str(exc.value)


def test_parse_llm_response_missing_recs_list(candidates):
    raw_response = '{"summary": "No list"}'

    with pytest.raises(LLMParseError) as exc:
        parse_llm_response(raw_response, candidates)
    assert "missing the 'recommendations' list" in str(exc.value)
