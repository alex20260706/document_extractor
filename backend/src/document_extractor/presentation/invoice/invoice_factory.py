"""Dependency composition for invoice extraction."""

from collections.abc import Sequence

from document_extractor.application.invoice.extract_invoice import (
    ExtractInvoice,
)
from document_extractor.domain.common.ports import (
    DocumentContentReaderPort,
    StructuredLlmClientPort,
)
from document_extractor.infrastructure.invoice.llm_invoice_enricher import (
    InvoiceLlmEnricher,
)
from document_extractor.infrastructure.invoice.rule_based_parser import (
    RuleBasedInvoiceParser,
)
from document_extractor.presentation.invoice.extraction_strategy import (
    InvoiceExtractionStrategy,
)


def build_invoice_strategy(
    readers: Sequence[DocumentContentReaderPort],
    llm_client: StructuredLlmClientPort | None = None,
    llm_max_input_characters: int = 60_000,
) -> InvoiceExtractionStrategy:
    """Compose the complete invoice extraction strategy.

    Args:
        readers: Shared document content readers.
        llm_client: Optional structured LLM client.
        llm_max_input_characters: Maximum context sent to the LLM.

    Returns:
        A configured HTTP-facing invoice strategy.
    """

    use_case = ExtractInvoice(
        readers=readers,
        parser=RuleBasedInvoiceParser(),
        enricher=(
            InvoiceLlmEnricher(
                llm_client,
                max_input_characters=llm_max_input_characters,
            )
            if llm_client
            else None
        ),
    )
    return InvoiceExtractionStrategy(use_case)
