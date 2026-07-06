"""Ports for invoice parsing and semantic enrichment."""

from typing import Protocol

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.domain.invoice.models import (
    InvoiceData,
    InvoiceEnrichmentPatch,
    InvoiceExtractionResult,
)


class InvoiceParserPort(Protocol):
    """Contract for interpreting readable text as an invoice."""

    def parse(
        self,
        text: str,
        acquisition_method: ContentAcquisitionMethod,
    ) -> InvoiceExtractionResult:
        """Parse text into a normalized invoice result.

        Args:
            text: Readable document text.
            acquisition_method: Method used to obtain the text.

        Returns:
            The locally extracted invoice result.
        """

        ...


class InvoiceEnricherPort(Protocol):
    """Contract for LLM fallback over unresolved invoice fields."""

    method: DataExtractionMethod

    def enrich(
        self,
        text: str,
        current_data: InvoiceData,
        request: EnrichmentRequest,
    ) -> InvoiceEnrichmentPatch | None:
        """Extract the requested invoice fields semantically.

        Args:
            text: Readable document text.
            current_data: Data produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            An enrichment patch, or ``None`` on controlled failure.
        """

        ...
