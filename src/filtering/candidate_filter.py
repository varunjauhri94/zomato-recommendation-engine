"""Deterministic candidate filtering (no LLM)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.models.preferences import Budget, UserPreferences
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

EMPTY_MESSAGE_DEFAULT = (
    "No restaurants found. Try a different location or lower your minimum rating."
)
EMPTY_MESSAGE_BUDGET = (
    "No restaurants in your budget range. Try a different budget level."
)
EMPTY_MESSAGE_LOCATION = (
    "No restaurants found in '{location}'. This dataset is primarily Bangalore-based."
)


@dataclass
class FilterResult:
    """Structured filter output with metadata for orchestration and UI."""

    candidates: List[Restaurant] = field(default_factory=list)
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0


def _effective_top_n(top_n: Optional[int]) -> int:
    settings = get_settings()
    if top_n is None or top_n <= 0:
        if top_n is not None and top_n <= 0:
            logger.warning("Invalid top_n=%s; using TOP_N_CANDIDATES=%d", top_n, settings.top_n_candidates)
        return settings.top_n_candidates
    return top_n


def _matches_location(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    target = prefs.normalized_location.lower()
    return (
        restaurant.city.lower() == target
        or target in restaurant.location.lower()
    )


def _matches_cuisine(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    if not prefs.cuisine_filter_active:
        return True
    needle = prefs.normalized_cuisine
    # Literal substring match (not regex) — edge case F-08, F-09
    return needle in restaurant.cuisine.lower()


def _matches_min_rating(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    if prefs.min_rating <= 0:
        return True
    if restaurant.rating is None:
        return False
    return restaurant.rating >= prefs.min_rating


def _matches_budget(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    band = restaurant.budget_band
    if band == "unknown":
        # Exclude unknown cost from strict budget filters (edge case F-07)
        return False
    return band == prefs.budget.value


def _sort_key(restaurant: Restaurant) -> tuple:
    """Rating desc, then name asc for stable tie-breaking (edge case F-11)."""
    rating = restaurant.rating if restaurant.rating is not None else -1.0
    return (-rating, restaurant.name.lower(), restaurant.id)


def _empty_message(
    prefs: UserPreferences,
    *,
    after_location: int,
    after_cuisine: int,
    after_rating: int,
    after_budget: int,
) -> str:
    if after_location == 0:
        return EMPTY_MESSAGE_LOCATION.format(location=prefs.normalized_location)
    if after_cuisine == 0 or after_rating == 0:
        return EMPTY_MESSAGE_DEFAULT
    if after_budget == 0:
        return EMPTY_MESSAGE_BUDGET
    return EMPTY_MESSAGE_DEFAULT


def filter_restaurants(
    restaurants: List[Restaurant],
    prefs: UserPreferences,
    *,
    top_n: Optional[int] = None,
) -> FilterResult:
    """
    Apply deterministic filters: location → cuisine → min_rating → budget → top_n.

    Returns FilterResult with candidates (may be empty) and metadata.
    Never raises for empty matches.
    """
    limit = _effective_top_n(top_n)
    settings = get_settings()

    if not restaurants:
        logger.error("filter_restaurants called with empty restaurant list")
        return FilterResult(
            candidates=[],
            message="Restaurant data is not loaded.",
            metadata={
                "candidates_considered": 0,
                "filters_applied": _filters_applied_dict(prefs),
                "llm_called": False,
            },
        )

    after_location = [r for r in restaurants if _matches_location(r, prefs)]
    after_cuisine = [r for r in after_location if _matches_cuisine(r, prefs)]
    after_rating = [r for r in after_cuisine if _matches_min_rating(r, prefs)]
    after_budget = [r for r in after_rating if _matches_budget(r, prefs)]

    after_location_count = len(after_location)
    after_cuisine_count = len(after_cuisine)
    after_rating_count = len(after_rating)

    sorted_matches = sorted(after_budget, key=_sort_key)
    candidates = sorted_matches[:limit]

    metadata: Dict[str, Any] = {
        "candidates_considered": len(restaurants),
        "after_location": after_location_count,
        "after_cuisine": after_cuisine_count,
        "after_rating": after_rating_count,
        "after_budget": len(after_budget),
        "returned": len(candidates),
        "top_n": limit,
        "filters_applied": _filters_applied_dict(prefs),
        "llm_called": False,
    }

    if not candidates:
        message = _empty_message(
            prefs,
            after_location=after_location_count,
            after_cuisine=after_cuisine_count,
            after_rating=after_rating_count,
            after_budget=len(after_budget),
        )
        logger.debug(
            "Filter empty: location=%s cuisine=%s budget=%s min_rating=%s counts=%s",
            prefs.normalized_location,
            prefs.cuisine,
            prefs.budget.value,
            prefs.min_rating,
            metadata,
        )
        return FilterResult(candidates=[], message=message, metadata=metadata)

    logger.debug(
        "Filter applied: returned=%d after_budget=%d top_n=%d",
        len(candidates),
        len(after_budget),
        limit,
    )
    return FilterResult(candidates=candidates, message=None, metadata=metadata)


def _filters_applied_dict(prefs: UserPreferences) -> Dict[str, Any]:
    applied: Dict[str, Any] = {
        "location": prefs.normalized_location,
        "budget": prefs.budget.value,
        "min_rating": prefs.min_rating,
    }
    if prefs.cuisine_filter_active:
        applied["cuisine"] = prefs.normalized_cuisine
    else:
        applied["cuisine"] = "any"
    if prefs.additional_preferences:
        applied["additional_preferences"] = prefs.additional_preferences
    return applied
