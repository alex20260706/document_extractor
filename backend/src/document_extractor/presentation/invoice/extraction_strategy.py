"""HTTP-facing invoice extraction strategy."""

from document_extractor.application.invoice.extract_invoice import (
    ExtractInvoice,
)
from document_extractor.application.invoice.extract_invoice_command import (
    ExtractInvoiceCommand,
)
from document_extractor.domain.common.enums import DocumentKind
from document_extractor.presentation.invoice.schemas import (
    InvoiceExtractionResponse,
)


class InvoiceExtractionStrategy:
    """Adapt the invoice use case to generic document dispatching."""

    document_kind = DocumentKind.INVOICE

    def __init__(self, use_case: ExtractInvoice) -> None:
        """Initialize the strategy with its invoice use case.

        Args:
            use_case: Configured invoice extraction workflow.
        """
        self._use_case = use_case

    def execute(
        self,
        content: bytes,
        filename: str,
        media_type: str,
    ) -> InvoiceExtractionResponse:
        """Run invoice extraction and translate its domain result.

        Args:
            content: Raw document content.
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            The invoice API response.
        """

        result = self._use_case.execute(
            ExtractInvoiceCommand(
                content=content,
                filename=filename,
                media_type=media_type,
            )
        )
        return InvoiceExtractionResponse.from_domain(result)
