"""Dependency composition for the document-extraction API."""

from functools import lru_cache

from document_extractor.infrastructure.config import get_settings
from document_extractor.presentation.common.controller import (
    DocumentExtractionController,
)
from document_extractor.presentation.common.llm_client_factory import (
    build_llm_client,
)
from document_extractor.presentation.common.reader_factory import (
    build_content_readers,
)
from document_extractor.presentation.common.strategies import (
    ExtractionStrategyRegistry,
)
from document_extractor.presentation.invoice.invoice_factory import (
    build_invoice_strategy,
)
from document_extractor.presentation.purchase_order.purchase_order_factory import (  # noqa: E501
    build_purchase_order_strategy,
)


@lru_cache
def get_extraction_controller() -> DocumentExtractionController:
    """Return the process-wide controller with all enabled strategies.

    Returns:
        A cached controller sharing configured readers and LLM client.
    """

    settings = get_settings()
    readers = build_content_readers(settings)
    llm_client = build_llm_client(settings)

    enabled_strategies = (
        build_invoice_strategy(
            readers,
            llm_client=llm_client,
            llm_max_input_characters=settings.llm_max_input_characters,
        ),
        build_purchase_order_strategy(
            readers,
            llm_client=llm_client,
            llm_max_input_characters=settings.llm_max_input_characters,
        ),
    )

    strategy_registry = ExtractionStrategyRegistry(enabled_strategies)

    return DocumentExtractionController(
        strategy_registry,
        settings.max_upload_mb * 1024 * 1024,
    )
