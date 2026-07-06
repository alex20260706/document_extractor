"""Ports for purchase-order parsing and semantic enrichment."""

from typing import Protocol

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderData,
    PurchaseOrderEnrichmentPatch,
    PurchaseOrderExtractionResult,
)


class PurchaseOrderParserPort(Protocol):
    """Contract for interpreting text as a purchase order."""

    def parse(
        self, text: str, acquisition_method: ContentAcquisitionMethod
    ) -> PurchaseOrderExtractionResult:
        """Parse text into a normalized purchase-order result.

        Args:
            text: Readable document text.
            acquisition_method: Method used to obtain the text.

        Returns:
            The locally extracted purchase-order result.
        """
        ...


class PurchaseOrderEnricherPort(Protocol):
    """Contract for semantic purchase-order enrichment."""

    method: DataExtractionMethod

    def enrich(
        self,
        text: str,
        current_data: PurchaseOrderData,
        request: EnrichmentRequest,
    ) -> PurchaseOrderEnrichmentPatch | None:
        """Extract the requested purchase-order fields semantically.

        Args:
            text: Readable document text.
            current_data: Data produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            An enrichment patch, or ``None`` on controlled failure.
        """
        ...
