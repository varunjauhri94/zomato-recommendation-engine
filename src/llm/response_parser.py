"""Parser for LLM recommendation responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.models.recommendation import Recommendation, RecommendationResponse
from src.models.restaurant import Restaurant
from src.llm.client import LLMAPIError

logger = logging.getLogger(__name__)


class LLMParseError(LLMAPIError):
    """Raised when the LLM response cannot be parsed or lacks required fields."""


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code block fences like ```json ... ``` (edge case L-08)."""
    stripped = text.strip()
    # Match ```json or ``` at the beginning, and ``` at the end
    stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
    stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_llm_response(
    raw: str,
    candidates: List[Restaurant],
) -> RecommendationResponse:
    """
    Parse raw LLM response string into RecommendationResponse.

    Args:
        raw: The raw text response from the LLM.
        candidates: The pre-filtered candidate list sent to the prompt.

    Returns:
        RecommendationResponse populated with ground-truth Restaurant data.

    Raises:
        LLMParseError: If parsing fails and cannot be recovered.
    """
    # 1. Clean code fences
    cleaned = _strip_markdown_fences(raw)

    # 2. Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM response as JSON. Raw preview: %s", cleaned[:200])
        raise LLMParseError(
            "We couldn't generate recommendations right now. Please try again."
        ) from exc

    if not isinstance(data, dict):
        raise LLMParseError("LLM response is not a JSON object.")

    # 3. Extract top-level fields
    summary = data.get("summary")
    if isinstance(summary, str):
        summary = summary.strip() or None
    else:
        summary = None

    raw_recs = data.get("recommendations")
    if not isinstance(raw_recs, list):
        # Edge case PA-10: Zero or missing recommendations list
        raise LLMParseError("LLM response is missing the 'recommendations' list.")

    # 4. Map candidates by ID for O(1) lookup
    candidate_map = {c.id: c for c in candidates}
    
    valid_recommendations: List[Recommendation] = []
    warnings: List[str] = []

    # 5. Process and validate each recommendation
    for item in raw_recs:
        if not isinstance(item, dict):
            continue

        item_id = item.get("id")
        if item_id is None:
            # Edge case PA-04/PA-07: Missing id
            logger.warning("Missing restaurant 'id' in recommendation item.")
            continue
            
        item_id_str = str(item_id).strip()
        restaurant = candidate_map.get(item_id_str)
        
        if not restaurant:
            # Edge case PA-04: Hallucinated ID
            warning_msg = f"Hallucinated candidate ID '{item_id_str}' dropped."
            logger.warning(warning_msg)
            warnings.append(warning_msg)
            continue

        explanation = item.get("explanation")
        # Edge case PA-08: Missing explanation
        if not isinstance(explanation, str) or not explanation.strip():
            explanation = "Recommended based on your preferences."
        else:
            explanation = explanation.strip()

        # Parse rank if provided, or default to a huge number to sort last
        raw_rank = item.get("rank")
        try:
            rank_val = int(raw_rank) if raw_rank is not None else 9999
        except (ValueError, TypeError):
            rank_val = 9999

        # Ensure name, rating, cost are NEVER taken from LLM (PA-11)
        # Create recommendation object
        rec = Recommendation(
            rank=rank_val,
            restaurant=restaurant,
            explanation=explanation,
        )
        valid_recommendations.append(rec)

    # 6. Sort and sequentialize ranks (PA-06, PA-07)
    # Sort by the LLM's provided rank, then by ID to keep it stable
    valid_recommendations.sort(key=lambda r: (r.rank, r.restaurant.id))

    final_recs: List[Recommendation] = []
    for index, rec in enumerate(valid_recommendations, start=1):
        # Re-assign sequential rank (1, 2, 3...)
        final_recs.append(
            Recommendation(
                rank=index,
                restaurant=rec.restaurant,
                explanation=rec.explanation,
            )
        )

    # 7. Check if we have any valid recommendations left
    if not final_recs:
        # Edge case PA-05: All IDs hallucinated or dropped
        raise LLMParseError(
            "We couldn't generate recommendations right now. Please try again."
        )

    status = "success"
    if warnings:
        status = "partial"

    return RecommendationResponse(
        status=status,
        summary=summary,
        recommendations=final_recs,
        warnings=warnings,
        metadata={
            "llm_called": True,
        },
    )
