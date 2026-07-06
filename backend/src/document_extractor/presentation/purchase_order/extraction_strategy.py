"""HTTP-facing purchase-order extraction strategy."""

from document_extractor.application.purchase_order.extract_purchase_order import (  # noqa: E501
    ExtractPurchaseOrder,
)
from document_extractor.application.purchase_order.extract_purchase_order_command import (  # noqa: E501
    ExtractPurchaseOrderCommand,
)
from document_extractor.domain.common.enums import DocumentKind
from document_extractor.presentation.purchase_order.schemas import (
    PurchaseOrderExtractionResponse,
)


class PurchaseOrderExtractionStrategy:
    """Adapt the purchase-order use case to generic dispatching."""

    document_kind = DocumentKind.PURCHASE_ORDER

    def __init__(self, use_case: ExtractPurchaseOrder) -> None:
        """Initialize the strategy with its purchase-order use case.

        Args:
            use_case: Configured purchase-order extraction workflow.
        """
        self._use_case = use_case

    def execute(
        self, content: bytes, filename: str, media_type: str
    ) -> PurchaseOrderExtractionResponse:
        """Run extraction and translate its domain result.

        Args:
            content: Raw document content.
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            The purchase-order API response.
        """
        result = self._use_case.execute(
            ExtractPurchaseOrderCommand(content, filename, media_type)
        )
        return PurchaseOrderExtractionResponse.from_domain(result)
