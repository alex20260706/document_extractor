"""Composition of the optional structured LLM client."""

import logging

from document_extractor.domain.common.ports import StructuredLlmClientPort
from document_extractor.infrastructure.config import Settings
from document_extractor.infrastructure.llm.openai_compatible_client import (
    OpenAiCompatibleJsonClient,
)

logger = logging.getLogger(__name__)


def build_llm_client(
    settings: Settings,
) -> StructuredLlmClientPort | None:
    """Build the shared LLM client when its provider is configured.

    Args:
        settings: Runtime provider configuration.

    Returns:
        A structured LLM client, or ``None`` when enrichment is disabled
        or no provider settings are supplied.

    Raises:
        RuntimeError: If provider settings are partially configured.
    """

    if not settings.llm_enabled:
        return None
    api_key = (
        settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
    )
    provider_settings = (
        settings.llm_base_url,
        api_key,
        settings.llm_model,
    )
    if not any(provider_settings):
        logger.warning(
            "Hybrid extraction is enabled, but no LLM provider is configured; "
            "local extraction will remain available"
        )
        return None
    if not all(provider_settings):
        raise RuntimeError(
            "Incomplete LLM configuration: LLM_BASE_URL, LLM_API_KEY and "
            "LLM_MODEL must be provided together."
        )
    return OpenAiCompatibleJsonClient(
        base_url=settings.llm_base_url,
        api_key=api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
        strict_schema=settings.llm_strict_schema,
    )
