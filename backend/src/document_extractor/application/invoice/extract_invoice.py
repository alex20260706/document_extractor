"""Local-first invoice extraction orchestration."""

import logging
from collections.abc import Sequence

from document_extractor.application.common.acquire_content import (
    acquire_document_content,
)
from document_extractor.application.common.enrichment_policy import (
    decide_enrichment,
)
from document_extractor.application.invoice.extract_invoice_command import (
    ExtractInvoiceCommand,
)
from document_extractor.domain.common.models import DocumentReadError
from document_extractor.domain.common.ports import DocumentContentReaderPort
from document_extractor.domain.invoice.assessment import assess_invoice
from document_extractor.domain.invoice.merger import merge_invoice_patch
from document_extractor.domain.invoice.models import InvoiceExtractionResult
from document_extractor.domain.invoice.ports import (
    InvoiceEnricherPort,
    InvoiceParserPort,
)

logger = logging.getLogger(__name__)


class ExtractInvoice:
    """Parse an invoice and use an LLM only for unresolved data."""

    def __init__(
        self,
        readers: Sequence[DocumentContentReaderPort],
        parser: InvoiceParserPort,
        enricher: InvoiceEnricherPort | None = None,
    ) -> None:
        """Initialize the use case with its extraction dependencies.

        Args:
            readers: Content readers in evaluation order.
            parser: Local invoice parser.
            enricher: Optional semantic enrichment provider.
        """
        self._readers = readers
        self._parser = parser
        self._enricher = enricher

    def execute(
        self, command: ExtractInvoiceCommand
    ) -> InvoiceExtractionResult:
        """Execute the local-first invoice extraction workflow.

        Args:
            command: Uploaded document and its file metadata.

        Returns:
            A normalized invoice result, including controlled failures.
        """

        try:
            content = acquire_document_content(
                readers=self._readers,
                content=command.content,
                filename=command.filename,
                media_type=command.media_type,
            )
        except DocumentReadError as error:
            return InvoiceExtractionResult.failed(error.code, error.message)

        if content is None:
            return InvoiceExtractionResult.failed(
                code="content_unavailable",
                message=(
                    "No readable text could be obtained from the document."
                ),
            )

        local_result = self._parser.parse(
            content.text,
            content.acquisition_method,
        )
        if local_result.data is None:
            logger.info("LLM enrichment skipped: local extraction has no data")
            return local_result
        if self._enricher is None:
            logger.info("LLM enrichment skipped: no provider is available")
            return local_result

        assessment = assess_invoice(local_result.data)
        logger.info(
            "Invoice assessment completed: missing=%s, low_confidence=%s, "
            "reliable_coverage=%.2f",
            assessment.missing_fields,
            assessment.low_confidence_fields,
            assessment.reliable_coverage,
        )
        request = decide_enrichment(assessment)
        if request is None:
            logger.info("LLM enrichment skipped: no target fields")
            return local_result

        logger.info(
            "LLM enrichment requested: target_fields=%s, full_extraction=%s",
            request.target_fields,
            request.full_extraction,
        )
        patch = self._enricher.enrich(
            text=content.text,
            current_data=local_result.data,
            request=request,
        )
        if patch is None:
            logger.info("LLM enrichment returned no patch")
            return local_result
        logger.info(
            "LLM enrichment returned patch: fields=%s, line_items_present=%s",
            tuple(patch.fields.keys()),
            patch.line_items is not None,
        )
        return merge_invoice_patch(local_result, patch, request)
