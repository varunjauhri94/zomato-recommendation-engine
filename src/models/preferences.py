"""User preference models with validation."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.config import get_settings

MAX_ADDITIONAL_PREFERENCES_LEN = 500
CUISINE_ANY_TOKENS = frozenset({"any", "*", "all"})


class Budget(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserPreferences(BaseModel):
    """Validated user inputs for restaurant filtering and LLM ranking."""

    location: str = Field(..., min_length=1, description="City e.g. Bangalore, Delhi")
    budget: Budget
    cuisine: str = Field(..., min_length=1, description="Cuisine type or 'any'")
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional_preferences: Optional[str] = Field(
        default=None,
        description="Free-text preferences passed to LLM in later phases",
    )

    model_config = {"frozen": True}

    @field_validator("location", "cuisine", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: object) -> object:
        if value is None:
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must not be empty")
            return stripped
        return value

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def _normalize_additional(cls, value: object) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > MAX_ADDITIONAL_PREFERENCES_LEN:
            return text[:MAX_ADDITIONAL_PREFERENCES_LEN]
        return text

    @property
    def normalized_location(self) -> str:
        return get_settings().normalize_location(self.location)

    @property
    def cuisine_filter_active(self) -> bool:
        return self.cuisine.strip().lower() not in CUISINE_ANY_TOKENS

    @property
    def normalized_cuisine(self) -> str:
        return self.cuisine.strip().lower()
