"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hf_dataset_id: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        alias="HF_DATASET_ID",
    )
    hf_home: Optional[str] = Field(default=None, alias="HF_HOME")

    top_n_candidates: int = Field(default=30, alias="TOP_N_CANDIDATES")
    top_k_recommendations: int = Field(default=5, alias="TOP_K_RECOMMENDATIONS")

    budget_low_max: int = Field(default=500, alias="BUDGET_LOW_MAX")
    budget_medium_max: int = Field(default=1500, alias="BUDGET_MEDIUM_MAX")

    data_cache_path: str = Field(
        default="data/cache/restaurants.pkl",
        alias="DATA_CACHE_PATH",
    )
    use_data_cache: bool = Field(default=True, alias="USE_DATA_CACHE")

    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="LLM_MODEL",
    )
    llm_temperature: float = Field(
        default=0.3,
        alias="LLM_TEMPERATURE",
    )

    @field_validator("top_n_candidates", "top_k_recommendations", mode="before")
    @classmethod
    def _positive_int(cls, value: object) -> object:
        if value is None or value == "":
            return value
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("must be positive")
        return parsed

    @field_validator("budget_low_max", "budget_medium_max", mode="before")
    @classmethod
    def _non_negative_int(cls, value: object) -> object:
        if value is None or value == "":
            return value
        return int(value)

    @field_validator("llm_temperature", mode="before")
    @classmethod
    def _temperature_bound(cls, value: object) -> object:
        if value is None or value == "":
            return value
        parsed = float(value)
        if parsed < 0.0 or parsed > 2.0:
            raise ValueError("must be between 0.0 and 2.0")
        return parsed


    @property
    def location_aliases(self) -> Dict[str, str]:
        """Map user-facing location variants to canonical city names."""
        return {
            "bengaluru": "Bangalore",
            "bangalore": "Bangalore",
            "new delhi": "Delhi",
            "delhi": "Delhi",
            "gurugram": "Gurgaon",
            "gurgaon": "Gurgaon",
            "bombay": "Mumbai",
            "mumbai": "Mumbai",
        }

    def normalize_location(self, location: str) -> str:
        key = location.strip().lower()
        return self.location_aliases.get(key, location.strip().title())

    def cost_to_budget_band(self, cost: Optional[int]) -> str:
        """Map cost for two (INR) to low / medium / high."""
        if cost is None or cost <= 0:
            return "unknown"
        if cost <= self.budget_low_max:
            return "low"
        if cost <= self.budget_medium_max:
            return "medium"
        return "high"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Module-level shortcuts
settings = get_settings()
