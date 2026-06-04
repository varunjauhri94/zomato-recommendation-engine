"""Canonical restaurant entity."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

BudgetBand = Literal["low", "medium", "high", "unknown"]


class Restaurant(BaseModel):
    """Normalized restaurant record from the Zomato dataset."""

    id: str
    name: str
    location: str
    city: str
    cuisine: str
    rating: Optional[float] = None
    cost_for_two: Optional[int] = None
    budget_band: BudgetBand = "unknown"
    raw: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
