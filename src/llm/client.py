"""Groq LLM Client implementation and interface."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Protocol

from groq import Groq
from groq import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

from src.config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for all LLM client errors."""


class LLMConfigurationError(LLMError):
    """Raised when the LLM configuration (e.g. API key) is missing or invalid."""


class LLMAPIError(LLMError):
    """Raised when the LLM API returns an error or fails to respond."""


class LLMTimeoutError(LLMAPIError):
    """Raised when the LLM API request times out."""


class LLMRateLimitError(LLMAPIError):
    """Raised when the LLM API rate limit is exceeded."""


class LLMClient(Protocol):
    """Protocol defining the interface for LLM clients."""

    def complete(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Send a prompt to the LLM and return the raw string response.

        Args:
            prompt: The user input prompt.
            system_instruction: Optional system message instruction.

        Returns:
            The raw text response from the model (typically JSON format).
        """
        ...


class GroqLLMClient:
    """LLM client implementation using the Groq SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.llm_model

        if not self.api_key:
            # Edge case L-01: Key missing
            raise LLMConfigurationError(
                "LLM API key is not configured. Set GROQ_API_KEY in .env."
            )

        try:
            self._client = Groq(api_key=self.api_key)
        except Exception as exc:
            raise LLMConfigurationError(f"Failed to initialize Groq client: {exc}") from exc

    def complete(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Call the Groq API with retries and timeout handling."""
        settings = get_settings()
        temperature = settings.llm_temperature

        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        # Retry once on transient errors (L-03, L-04, L-10)
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    "LLM request: model=%s, temperature=%.2f, attempt=%d",
                    self.model,
                    temperature,
                    attempt,
                )
                start_time = time.perf_counter()
                
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    timeout=30.0,  # 30 second timeout
                )
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info("LLM request completed in %.0f ms", duration_ms)
                
                content = response.choices[0].message.content
                if not content:
                    # Edge case L-06: Empty response
                    if attempt < max_attempts:
                        logger.warning("Empty response from Groq API, retrying...")
                        continue
                    raise LLMAPIError("Received empty response from LLM API.")
                
                return content

            except AuthenticationError as exc:
                # Edge case L-02: Auth error (no retry)
                logger.error("Groq Authentication Error: %s", exc)
                raise LLMConfigurationError(
                    "Invalid API configuration. Check your API key."
                ) from exc

            except APITimeoutError as exc:
                # Edge case L-03: Timeout
                logger.warning("Groq API Timeout on attempt %d: %s", attempt, exc)
                if attempt < max_attempts:
                    time.sleep(1)
                    continue
                raise LLMTimeoutError(
                    "Recommendations temporarily unavailable. Please try again."
                ) from exc

            except RateLimitError as exc:
                # Edge case L-04: Rate limit
                logger.warning("Groq API Rate Limit on attempt %d: %s", attempt, exc)
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
                    continue
                raise LLMRateLimitError(
                    "Service is busy. Please try again in a moment."
                ) from exc

            except APIConnectionError as exc:
                # Edge case L-10: Connection error
                logger.warning("Groq API Connection Error on attempt %d: %s", attempt, exc)
                if attempt < max_attempts:
                    time.sleep(1)
                    continue
                raise LLMAPIError(
                    "Recommendations temporarily unavailable. Please try again."
                ) from exc

            except APIStatusError as exc:
                # Edge case L-05: Model not found, or other server status code
                logger.error("Groq API Status Error: %s", exc)
                if exc.status_code == 404:
                    raise LLMConfigurationError(
                        f"LLM model configuration error. Model '{self.model}' not found."
                    ) from exc
                if attempt < max_attempts and exc.status_code >= 500:
                    time.sleep(1)
                    continue
                raise LLMAPIError(
                    f"Groq API returned status code {exc.status_code}: {exc.message}"
                ) from exc

            except Exception as exc:
                logger.error("Unexpected error in Groq client: %s", exc)
                raise LLMAPIError(f"Unexpected LLM client error: {exc}") from exc

        raise LLMAPIError("Failed to get response after retries.")


class FakeLLMClient:
    """Mock LLM client yielding static JSON payloads for testing."""

    def __init__(self, response_text: Optional[str] = None, should_raise: Optional[Exception] = None):
        self.response_text = response_text
        self.should_raise = should_raise
        self.calls: List[Dict[str, Any]] = []

    def complete(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        self.calls.append({"prompt": prompt, "system_instruction": system_instruction})
        
        if self.should_raise:
            raise self.should_raise
            
        if self.response_text is not None:
            return self.response_text
            
        # Return default valid JSON response matching RecommendationResponse outline
        return """
        {
            "summary": "Fake summary recommendation.",
            "recommendations": [
                {
                    "id": "1",
                    "rank": 1,
                    "explanation": "Fake explanation for candidate 1."
                }
            ]
        }
        """
