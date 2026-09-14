"""Single Gemini API gateway with retry/backoff and JSON schema validation.

All Gemini calls route through this module. The API key never leaves the backend.
"""

import asyncio
import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Centralized Gemini API client with retry, backoff, and response validation."""

    def __init__(self) -> None:
        """Initialize the Gemini client."""
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set. Gemini calls will fail.")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        # LRU cache for identical prompts — avoids redundant API calls
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_max_size = 64

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate a response from Gemini with optional JSON schema enforcement.

        Args:
            prompt: The user/task prompt.
            system_instruction: System-level instruction for the model.
            response_schema: Pydantic model to validate and enforce JSON output.
            temperature: Sampling temperature (lower = more deterministic).
            max_output_tokens: Maximum tokens in the response.

        Returns:
            Parsed and validated response dictionary.

        Raises:
            ValueError: If response fails schema validation after retries.
            ConnectionError: If API is unreachable after retries.
        """
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        # Check cache for identical prompt+schema combinations
        schema_name = response_schema.__name__ if response_schema else "none"
        cache_key = hashlib.sha256(
            f"{prompt}::{system_instruction}::{schema_name}::{temperature}".encode()
        ).hexdigest()

        if cache_key in self._cache:
            logger.debug("Cache hit for prompt hash %s", cache_key[:8])
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        generate_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **config_kwargs,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=generate_config,
            )
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            raise

        # Extract text from response
        if not response.text:
            logger.error("Gemini returned empty response")
            msg = "Gemini returned an empty response"
            raise ValueError(msg)

        response_text = response.text.strip()

        # Parse and validate JSON if schema provided
        if response_schema is not None:
            result = self._validate_json_response(response_text, response_schema)
        else:
            result = {"text": response_text}

        # Store in cache
        self._cache[cache_key] = result
        if len(self._cache) > self._cache_max_size:
            self._cache.popitem(last=False)

        return result

    def _validate_json_response(
        self,
        response_text: str,
        schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Parse and validate a JSON response against a Pydantic schema.

        Args:
            response_text: Raw text from Gemini.
            schema: Pydantic model to validate against.

        Returns:
            Validated dictionary.

        Raises:
            ValueError: If parsing or validation fails.
        """
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = response_text
            if "```json" in response_text:
                start = response_text.index("```json") + 7
                end = response_text.index("```", start)
                json_match = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.index("```") + 3
                end = response_text.index("```", start)
                json_match = response_text[start:end].strip()

            try:
                parsed = json.loads(json_match)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse Gemini JSON response: %s", response_text[:200])
                msg = f"Failed to parse Gemini response as JSON: {e}"
                raise ValueError(msg) from e

        try:
            validated = schema.model_validate(parsed)
            return validated.model_dump()
        except ValidationError as e:
            logger.error("Gemini response failed schema validation: %s", e)
            msg = f"Gemini response failed validation: {e}"
            raise ValueError(msg) from e

    def generate_with_document(
        self,
        prompt: str,
        document_text: str,
        system_instruction: str | None = None,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate with document context included in the prompt.

        Args:
            prompt: The task prompt.
            document_text: The document text to include as context.
            system_instruction: System instruction.
            response_schema: Pydantic schema for validation.
            temperature: Sampling temperature.

        Returns:
            Validated response dictionary.
        """
        full_prompt = (
            f"DOCUMENT TEXT:\n---\n{document_text[:50000]}\n---\n\n"
            f"TASK:\n{prompt}"
        )
        return self.generate(
            prompt=full_prompt,
            system_instruction=system_instruction,
            response_schema=response_schema,
            temperature=temperature,
        )

    async def generate_async(
        self,
        prompt: str,
        system_instruction: str | None = None,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Async wrapper for generate — runs in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(
            self.generate,
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=response_schema,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )


# Module-level singleton
_gemini_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """Get the singleton Gemini service instance."""
    global _gemini_service  # noqa: PLW0603
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
