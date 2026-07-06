import pytest

from document_extractor.infrastructure.config import Settings
from document_extractor.presentation.common.llm_client_factory import (
    build_llm_client,
)


def test_llm_is_disabled_without_external_configuration() -> None:
    assert build_llm_client(Settings(llm_enabled=False)) is None


def test_enabled_llm_without_provider_keeps_local_fallback() -> None:
    settings = Settings(
        llm_enabled=True,
        llm_base_url=None,
        llm_api_key=None,
        llm_model=None,
    )

    assert build_llm_client(settings) is None


def test_partial_llm_configuration_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Incomplete LLM configuration"):
        build_llm_client(
            Settings(
                llm_enabled=True,
                llm_base_url="https://provider.example/v1",
                llm_api_key=None,
                llm_model=None,
            )
        )


def test_builds_client_with_complete_configuration() -> None:
    client = build_llm_client(
        Settings(
            llm_enabled=True,
            llm_base_url="https://provider.example/v1",
            llm_api_key="secret",
            llm_model="model",
        )
    )

    assert client is not None
