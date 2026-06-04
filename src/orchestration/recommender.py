"""Orchestration pipeline for the recommendation system (Phase 4)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from src.models.preferences import UserPreferences
from src.models.recommendation import RecommendationResponse
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class RecommenderService:
    """
    Orchestrates candidate selection, prompt building, LLM inference, and parsing.

    Supports constructor dependency injection for testability.
    """

    def __init__(
        self,
        store: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        filter_fn: Optional[Callable] = None,
        prompt_builder_fn: Optional[Callable] = None,
        response_parser_fn: Optional[Callable] = None,
    ):
        self.store = store
        self.llm_client = llm_client
        self.filter_fn = filter_fn
        self.prompt_builder_fn = prompt_builder_fn
        self.response_parser_fn = response_parser_fn

    def _get_store(self) -> Any:
        if self.store is None:
            from src.data.store import get_store
            return get_store()
        return self.store

    def _get_llm_client(self) -> Any:
        if self.llm_client is None:
            from src.llm.client import GroqLLMClient
            return GroqLLMClient()
        return self.llm_client

    def _get_filter_fn(self) -> Callable:
        if self.filter_fn is None:
            from src.filtering.candidate_filter import filter_restaurants
            return filter_restaurants
        return self.filter_fn

    def _get_prompt_builder_fn(self) -> Callable:
        if self.prompt_builder_fn is None:
            from src.llm.prompt_builder import build_recommendation_prompt
            return build_recommendation_prompt
        return self.prompt_builder_fn

    def _get_response_parser_fn(self) -> Callable:
        if self.response_parser_fn is None:
            from src.llm.response_parser import parse_llm_response
            return parse_llm_response
        return self.response_parser_fn

    def recommend(self, prefs: UserPreferences) -> RecommendationResponse:
        """
        Executes the end-to-end recommendation workflow.

        1. Filters restaurants in-memory using preferences.
        2. Bypasses LLM if candidates list is empty.
        3. Invokes the LLM client to rank and explain candidates.
        4. Parses and merges the LLM recommendations with database records.
        """
        logger.info(
            "RecommenderService.recommend: location=%s budget=%s cuisine=%s min_rating=%s",
            prefs.location,
            prefs.budget.value,
            prefs.cuisine,
            prefs.min_rating,
        )

        # Ensure validation is run. (prefs is already a validated UserPreferences model,
        # but check for any unexpected type errors)
        if not isinstance(prefs, UserPreferences):
            raise TypeError("prefs must be an instance of UserPreferences")

        try:
            # 1. Fetch all restaurants from store
            store = self._get_store()
            restaurants = store.get_all()

            # 2. Filter candidates
            filter_fn = self._get_filter_fn()
            filter_result = filter_fn(restaurants, prefs)

            # 3. Guard empty state (ED-1, O-02)
            if filter_result.is_empty:
                logger.info("No candidates matched filters. Skipping LLM call.")
                metadata = filter_result.metadata.copy()
                metadata["llm_called"] = False
                return RecommendationResponse(
                    status="empty",
                    summary=None,
                    recommendations=[],
                    message=filter_result.message or "No restaurants found.",
                    warnings=[],
                    metadata=metadata,
                )

            # 4. Invoke LLM Engine
            from src.config import get_settings
            from src.llm.client import (
                LLMAPIError,
                LLMConfigurationError,
                LLMTimeoutError,
                LLMRateLimitError,
            )
            from src.llm.response_parser import LLMParseError

            settings = get_settings()
            top_k = settings.top_k_recommendations

            prompt_builder_fn = self._get_prompt_builder_fn()
            system_instruction, user_prompt = prompt_builder_fn(
                prefs, filter_result.candidates, top_k=top_k
            )

            client = self._get_llm_client()
            start_time = time.perf_counter()
            
            raw_response = client.complete(
                user_prompt, system_instruction=system_instruction
            )
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info("LLM complete finished in %.1f ms", elapsed_ms)

            # 5. Parse response
            response_parser_fn = self._get_response_parser_fn()
            response = response_parser_fn(raw_response, filter_result.candidates)

            # 6. Enrich metadata
            metadata = filter_result.metadata.copy()
            metadata.update(response.metadata)
            metadata["llm_called"] = True
            metadata["llm_latency_ms"] = round(elapsed_ms, 1)

            return response.model_copy(update={"metadata": metadata})

        except LLMConfigurationError as exc:
            logger.error("LLM configuration error in pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message=str(exc),
                metadata={"llm_called": False, "error_type": "LLMConfigurationError"},
            )
        except LLMTimeoutError as exc:
            logger.error("LLM timeout error in pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message="Recommendations temporarily unavailable. Please try again.",
                metadata={"llm_called": True, "error_type": "LLMTimeoutError"},
            )
        except LLMRateLimitError as exc:
            logger.error("LLM rate limit error in pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message="Service is busy. Please try again in a moment.",
                metadata={"llm_called": True, "error_type": "LLMRateLimitError"},
            )
        except LLMParseError as exc:
            logger.error("LLM parse error in pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message="We couldn't generate recommendations right now. Please try again.",
                metadata={"llm_called": True, "error_type": "LLMParseError"},
            )
        except LLMAPIError as exc:
            logger.error("LLM API error in pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message="Recommendations temporarily unavailable. Please try again.",
                metadata={"llm_called": True, "error_type": "LLMAPIError"},
            )
        except Exception as exc:
            logger.exception("Unexpected error in recommendation pipeline: %s", exc)
            return RecommendationResponse(
                status="error",
                message="Something went wrong. Please try again.",
                metadata={"llm_called": False, "error_type": "Exception", "error": str(exc)},
            )
