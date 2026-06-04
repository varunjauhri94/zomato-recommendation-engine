"""Unit tests for the LLM client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from groq import APITimeoutError, AuthenticationError, RateLimitError
from src.llm.client import (
    FakeLLMClient,
    GroqLLMClient,
    LLMAPIError,
    LLMConfigurationError,
    LLMTimeoutError,
    LLMRateLimitError,
)
from src.config import Settings


def test_fake_llm_client_default():
    client = FakeLLMClient()
    res = client.complete("Hello")
    assert "Fake summary recommendation" in res
    assert len(client.calls) == 1
    assert client.calls[0]["prompt"] == "Hello"


def test_fake_llm_client_custom():
    custom_text = '{"custom": "response"}'
    client = FakeLLMClient(response_text=custom_text)
    res = client.complete("Test")
    assert res == custom_text
    assert len(client.calls) == 1


def test_fake_llm_client_exception():
    client = FakeLLMClient(should_raise=ValueError("Some error"))
    with pytest.raises(ValueError) as exc:
        client.complete("Test")
    assert "Some error" in str(exc.value)


@patch("src.llm.client.get_settings")
def test_groq_llm_client_missing_key(mock_get_settings):
    # Setup settings to return empty API key
    mock_settings = MagicMock(spec=Settings)
    mock_settings.groq_api_key = None
    mock_settings.llm_model = "llama-3.3-70b-versatile"
    mock_get_settings.return_value = mock_settings

    with pytest.raises(LLMConfigurationError) as exc:
        GroqLLMClient()
    assert "LLM API key is not configured" in str(exc.value)


@patch("src.llm.client.Groq")
@patch("src.llm.client.get_settings")
def test_groq_llm_client_success(mock_get_settings, mock_groq_class):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.groq_api_key = "test-api-key"
    mock_settings.llm_model = "llama-3.3-70b-versatile"
    mock_settings.llm_temperature = 0.3
    mock_get_settings.return_value = mock_settings

    # Mock the response structure of Groq completion
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "ok"}'
    
    mock_groq_instance = MagicMock()
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq_class.return_value = mock_groq_instance

    client = GroqLLMClient()
    res = client.complete("My prompt", system_instruction="My system")

    assert res == '{"result": "ok"}'
    mock_groq_instance.chat.completions.create.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "My system"},
            {"role": "user", "content": "My prompt"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        timeout=30.0,
    )


@patch("src.llm.client.Groq")
@patch("src.llm.client.get_settings")
def test_groq_llm_client_retry_on_timeout(mock_get_settings, mock_groq_class):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.groq_api_key = "test-api-key"
    mock_settings.llm_model = "llama-3.3-70b-versatile"
    mock_settings.llm_temperature = 0.3
    mock_get_settings.return_value = mock_settings

    mock_groq_instance = MagicMock()
    
    # First call raises timeout, second call succeeds
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "ok"}'

    # Create dummy request and response objects to satisfy Groq exception signatures
    dummy_request = MagicMock()
    
    mock_groq_instance.chat.completions.create.side_effect = [
        APITimeoutError(request=dummy_request),
        mock_response,
    ]
    mock_groq_class.return_value = mock_groq_instance

    client = GroqLLMClient()
    res = client.complete("My prompt")

    assert res == '{"result": "ok"}'
    assert mock_groq_instance.chat.completions.create.call_count == 2


@patch("src.llm.client.Groq")
@patch("src.llm.client.get_settings")
def test_groq_llm_client_timeout_failure(mock_get_settings, mock_groq_class):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.groq_api_key = "test-api-key"
    mock_settings.llm_model = "llama-3.3-70b-versatile"
    mock_settings.llm_temperature = 0.3
    mock_get_settings.return_value = mock_settings

    mock_groq_instance = MagicMock()
    dummy_request = MagicMock()
    
    # Both calls raise timeout
    mock_groq_instance.chat.completions.create.side_effect = [
        APITimeoutError(request=dummy_request),
        APITimeoutError(request=dummy_request),
    ]
    mock_groq_class.return_value = mock_groq_instance

    client = GroqLLMClient()
    with pytest.raises(LLMTimeoutError) as exc:
        client.complete("My prompt")
    
    assert "Recommendations temporarily unavailable" in str(exc.value)
    assert mock_groq_instance.chat.completions.create.call_count == 2


@patch("src.llm.client.Groq")
@patch("src.llm.client.get_settings")
def test_groq_llm_client_authentication_failure(mock_get_settings, mock_groq_class):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.groq_api_key = "invalid-key"
    mock_settings.llm_model = "llama-3.3-70b-versatile"
    mock_settings.llm_temperature = 0.3
    mock_get_settings.return_value = mock_settings

    mock_groq_instance = MagicMock()
    dummy_request = MagicMock()
    dummy_response = MagicMock()
    
    # Auth error should not retry
    mock_groq_instance.chat.completions.create.side_effect = AuthenticationError(
        message="Invalid API Key",
        response=dummy_response,
        body=None,
    )
    mock_groq_class.return_value = mock_groq_instance

    client = GroqLLMClient()
    with pytest.raises(LLMConfigurationError) as exc:
        client.complete("My prompt")
    
    assert "Invalid API configuration. Check your API key." in str(exc.value)
    assert mock_groq_instance.chat.completions.create.call_count == 1
