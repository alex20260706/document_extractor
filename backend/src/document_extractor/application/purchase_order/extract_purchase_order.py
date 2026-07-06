"""Local-first purchase-order extraction orchestration."""

import logging
from collections.abc import Sequence

from document_extractor.application.common.acquire_content import (
    acquire_document_content,
)
from document_extractor.application.common.enrichment_policy import (
    decide_enrichment,
)
from document_extractor.application.purchase_order.extract_purchase_order_command import (  # noqa: E501
    ExtractPurchaseOrderCommand,
)
from document_extractor.domain.common.models import DocumentReadError
from document_extractor.domain.common.ports import DocumentContentReaderPort
from document_extractor.domain.purchase_order.assessment import (
    assess_purchase_order,
)
from document_extractor.domain.purchase_order.merger import (
    merge_purchase_order_patch,
)
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderExtractionResult,
)
from document_extractor.domain.purchase_order.ports import (
    PurchaseOrderEnricherPort,
    PurchaseOrderParserPort,
)

logger = logging.getLogger(__name__)


class ExtractPurchaseOrder:
    """Extract a purchase order locally and enrich unresolved data."""

    def __init__(
        self,
        readers: Sequence[DocumentContentReaderPort],
        parser: PurchaseOrderParserPort,
        enricher: PurchaseOrderEnricherPort | None = None,
    ) -> None:
        """Initialize the use case with its extraction dependencies.

        Args:
            readers: Content readers in evaluation order.
            parser: Local purchase-order parser.
            enricher: Optional semantic enrichment provider.
        """
        self._readers = readers
        self._parser = parser
        self._enricher = enricher

    def execute(
        self, command: ExtractPurchaseOrderCommand
    ) -> PurchaseOrderExtractionResult:
        """Execute the local-first purchase-order workflow.

        Args:
            command: Uploaded document and its file metadata.

        Returns:
            A normalized purchase-order result, including failures.
        """
        try:
            content = acquire_document_content(
                readers=self._readers,
                content=command.content,
                filename=command.filename,
                media_type=command.media_type,
            )
        except DocumentReadError as error:
            return PurchaseOrderExtractionResult.failed(
                error.code, error.message
            )
        if content is None:
            return PurchaseOrderExtractionResult.failed(
                "content_unavailable",
                "No readable text could be obtained from the document.",
            )

        local_result = self._parser.parse(
            text=content.text, acquisition_method=content.acquisition_method
        )
        if local_result.data is None or self._enricher is None:
            return local_result
        assessment = assess_purchase_order(local_result.data)
        request = decide_enrichment(assessment)
        if request is None:
            return local_result
        logger.info(
            "Purchase order enrichment requested: target_fields=%s, "
            "full_extraction=%s",
            request.target_fields,
            request.full_extraction,
        )
        patch = self._enricher.enrich(content.text, local_result.data, request)
        return (
            merge_purchase_order_patch(local_result, patch, request)
            if patch is not None
            else local_result
        )
