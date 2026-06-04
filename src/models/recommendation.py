"""Recommendation response models (Phase 3+)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.restaurant import Restaurant


class Recommendation(BaseModel):
    """A single ranked restaurant recommendation with an AI explanation."""

    rank: int = Field(..., ge=1, description="Rank position (1-indexed)")
    restaurant: Restaurant = Field(..., description="Canonical restaurant data")
    explanation: str = Field(..., min_length=1, description="AI-generated explanation")

    model_config = {"frozen": True}


class RecommendationResponse(BaseModel):
    """Top-K recommendations response with summary and process metadata."""

    status: str = Field(default="success", description="Status code e.g. success, empty, partial, error")
    summary: Optional[str] = Field(default=None, description="AI-generated overall summary")
    recommendations: List[Recommendation] = Field(default_factory=list, description="Ranked recommendation items")
    message: Optional[str] = Field(default=None, description="Human-readable fallback or empty-state text")
    warnings: List[str] = Field(default_factory=list, description="Warnings or issues encountered during the request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    model_config = {"frozen": True}
