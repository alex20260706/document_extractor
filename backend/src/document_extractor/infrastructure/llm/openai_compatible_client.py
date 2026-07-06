"""OpenAI-compatible adapter for structured JSON generation."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAiCompatibleJsonClient:
    """Request structured JSON from an OpenAI-compatible chat API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_output_tokens: int = 2_500,
        strict_schema: bool = False,
    ) -> None:
        """Configure the provider endpoint and generation limits.

        Args:
            base_url: Provider API base URL.
            api_key: Bearer token used to authenticate requests.
            model: Provider model identifier.
            timeout_seconds: Maximum request duration.
            max_output_tokens: Maximum generated response tokens.
            strict_schema: Whether the provider must enforce the schema.
        """
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._strict_schema = strict_schema

    def generate_json(
        self,
        schema_name: str,
        instructions: str,
        input_text: str,
        json_schema: dict[str, object],
    ) -> dict[str, object] | None:
        """Return parsed JSON, degrading cleanly on provider failure.

        Args:
            schema_name: Name identifying the response schema.
            instructions: System instructions for the model.
            input_text: Untrusted document context sent to the model.
            json_schema: Required JSON response structure.

        Returns:
            Parsed JSON, or ``None`` when the request or response fails.
        """

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            "temperature": 0,
            "max_tokens": self._max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": self._strict_schema,
                    "schema": json_schema,
                },
            },
        }
        try:
            response = httpx.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = (
                json.loads(content) if isinstance(content, str) else content
            )
            return parsed if isinstance(parsed, dict) else None
        # Provider and response failures are recoverable because local
        # extraction remains usable without semantic enrichment.
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ):
            logger.warning("Structured LLM request failed", exc_info=True)
            return None
