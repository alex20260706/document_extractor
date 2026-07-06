"""Dependency composition for purchase-order extraction."""

from collections.abc import Sequence

from document_extractor.application.purchase_order.extract_purchase_order import (  # noqa: E501
    ExtractPurchaseOrder,
)
from document_extractor.domain.common.ports import (
    DocumentContentReaderPort,
    StructuredLlmClientPort,
)
from document_extractor.infrastructure.purchase_order.llm_purchase_order_enricher import (  # noqa: E501
    PurchaseOrderLlmEnricher,
)
from document_extractor.infrastructure.purchase_order.rule_based_parser import (  # noqa: E501
    RuleBasedPurchaseOrderParser,
)
from document_extractor.presentation.purchase_order.extraction_strategy import (  # noqa: E501
    PurchaseOrderExtractionStrategy,
)


def build_purchase_order_strategy(
    readers: Sequence[DocumentContentReaderPort],
    llm_client: StructuredLlmClientPort | None = None,
    llm_max_input_characters: int = 60_000,
) -> PurchaseOrderExtractionStrategy:
    """Compose the complete purchase-order extraction strategy.

    Args:
        readers: Shared document content readers.
        llm_client: Optional structured LLM client.
        llm_max_input_characters: Maximum context sent to the LLM.

    Returns:
        A configured HTTP-facing purchase-order strategy.
    """

    return PurchaseOrderExtractionStrategy(
        ExtractPurchaseOrder(
            readers=readers,
            parser=RuleBasedPurchaseOrderParser(),
            enricher=(
                PurchaseOrderLlmEnricher(llm_client, llm_max_input_characters)
                if llm_client
                else None
            ),
        )
    )
