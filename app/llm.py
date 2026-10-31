"""Grok LLM client via xAI API (OpenAI-compatible)."""

import logging
import os
import time
from typing import AsyncGenerator

import openai
from openai import OpenAI

from app.config import settings

logger = logging.getLogger("uniassist.llm")

# Module-level state
_client: OpenAI | None = None
_active_model: str = ""


def _create_client() -> OpenAI:
    """Create the OpenAI client pointed at xAI."""
    return OpenAI(
        api_key=settings.xai_api_key,
        base_url=settings.xai_base_url,
        timeout=60.0,
        max_retries=3,
    )


def get_client() -> OpenAI:
    """Return the singleton OpenAI client."""
    global _client
    if _client is None:
        _client = _create_client()
    return _client


def detect_model() -> str:
    """
    Detect the best available Grok model.
    
    Tries the configured model first; if unavailable, picks the best
    'grok' chat model from the API's model list.
    """
    global _active_model

    if _active_model:
        return _active_model

    configured = settings.xai_model
    client = get_client()

    try:
        models_response = client.models.list()
        available = [m.id for m in models_response.data]
        logger.info(f"Available models: {available}")

        # Check if configured model is available
        if configured in available:
            _active_model = configured
            logger.info(f"Using configured model: {_active_model}")
            return _active_model

        # Filter for standard text/chat models (exclude robotics, embedding, audio, bidi)
        valid_chat_models = [
            m for m in available
            if ("grok" in m.lower() or "gemini" in m.lower())
            and not any(bad in m.lower() for bad in ["robotics", "embedding", "bidi", "audio", "whisper", "imagen"])
        ]
        
        # Prioritize fast, high-quality standard chat models
        priority_order = [
            "gemini-3.8-flash", "models/gemini-3.8-flash",
            "gemini-2.0-flash", "models/gemini-2.0-flash",
            "grok-4", "grok-beta", "grok-2",
            "gemini-1.5-flash", "models/gemini-1.5-flash"
        ]
        
        for p in priority_order:
            for m in valid_chat_models:
                if p in m:
                    _active_model = m
                    logger.info(f"Selected prioritized chat model: {_active_model}")
                    return _active_model

        if valid_chat_models:
            _active_model = valid_chat_models[0]
            logger.info(
                f"Configured model '{configured}' not in available list. "
                f"Using best available: {_active_model}"
            )
            return _active_model

        # Last resort: use configured and hope for the best
        _active_model = configured
        logger.warning(
            f"No preferred models found in API. Falling back to configured: {_active_model}"
        )
        return _active_model

    except Exception as e:
        logger.error(f"Failed to list models: {e}. Using configured: {configured}")
        _active_model = configured
        return _active_model


def get_active_model() -> str:
    """Return the currently active model name."""
    return _active_model or settings.xai_model


def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """
    Non-streaming chat completion with retries and backoff.
    
    Returns the assistant message content.
    """
    client = get_client()
    model = detect_model()

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return response.choices[0].message.content or ""

        except openai.RateLimitError:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
            time.sleep(wait)

        except openai.APITimeoutError:
            wait = 2 ** attempt
            logger.warning(f"Timeout, retrying in {wait}s (attempt {attempt + 1})")
            time.sleep(wait)

        except openai.APIError as e:
            logger.error(f"API error: {e}")
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("LLM call failed after 3 retries")


def chat_completion_stream(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Streaming chat completion. Yields content chunks.
    
    Note: This is a synchronous generator despite the name;
    it's wrapped in an async generator at the route level.
    """
    client = get_client()
    model = detect_model()

    for attempt in range(3):
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return  # Success, exit retry loop

        except openai.RateLimitError:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Rate limited during stream, retrying in {wait}s")
            time.sleep(wait)

        except openai.APITimeoutError:
            wait = 2 ** attempt
            logger.warning(f"Timeout during stream, retrying in {wait}s")
            time.sleep(wait)

        except openai.APIError as e:
            logger.error(f"Stream API error: {e}")
            if attempt == 2:
                yield "\n\n*Sorry, I encountered an error. Please try again.*"
                return
            time.sleep(2 ** attempt)


def check_llm_health() -> bool:
    """Quick health check — can we reach the API?"""
    try:
        client = get_client()
        client.models.list()
        return True
    except Exception:
        return False
