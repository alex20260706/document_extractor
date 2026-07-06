"""Domain models for invoice extraction."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
    DocumentKind,
    ExtractionStatus,
)
from document_extractor.domain.common.models import (
    ExtractedField,
    ExtractionError,
)


@dataclass(frozen=True, slots=True)
class Party:
    """A legal party identified in an invoice."""

    name: ExtractedField
    tax_id: ExtractedField


@dataclass(frozen=True, slots=True)
class InvoiceLine:
    """One product or service line extracted from an invoice."""

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    confidence: float = 0.0
    extraction_method: DataExtractionMethod | None = None

    def __post_init__(self) -> None:
        """Validate the normalized confidence value.

        Raises:
            ValueError: If confidence falls outside the inclusive
                ``0`` to ``1`` range.
        """
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Line confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class InvoiceData:
    """The structured business data extracted from an invoice."""

    invoice_number: ExtractedField
    issue_date: ExtractedField
    issuer: Party
    receiver: Party
    taxable_base: ExtractedField
    tax_amount: ExtractedField
    total_amount: ExtractedField
    currency: ExtractedField
    line_items: tuple[InvoiceLine, ...] = ()

    def field_items(self) -> tuple[tuple[str, ExtractedField], ...]:
        """Expose header fields in a stable API-friendly order.

        Returns:
            Field names and values in presentation order.
        """

        return (
            ("invoice_number", self.invoice_number),
            ("issue_date", self.issue_date),
            ("issuer_name", self.issuer.name),
            ("issuer_tax_id", self.issuer.tax_id),
            ("receiver_name", self.receiver.name),
            ("receiver_tax_id", self.receiver.tax_id),
            ("taxable_base", self.taxable_base),
            ("tax_amount", self.tax_amount),
            ("total_amount", self.total_amount),
            ("currency", self.currency),
        )


@dataclass(frozen=True, slots=True)
class InvoiceExtractionResult:
    """The normalized outcome of extracting an invoice."""

    status: ExtractionStatus
    data: InvoiceData | None
    acquisition_method: ContentAcquisitionMethod | None = None
    extraction_method: DataExtractionMethod | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[ExtractionError, ...] = ()

    @property
    def document_kind(self) -> DocumentKind:
        """Identify the extracted document type.

        Returns:
            The invoice document kind.
        """

        return DocumentKind.INVOICE

    @classmethod
    def failed(
        cls,
        code: str,
        message: str,
        acquisition_method: ContentAcquisitionMethod | None = None,
    ) -> Self:
        """Build a failed invoice result with one processing error.

        Args:
            code: Stable machine-readable error code.
            message: Human-readable error description.
            acquisition_method: Document reading method, if known.

        Returns:
            A failed invoice extraction result.
        """

        return cls(
            status=ExtractionStatus.FAILED,
            data=None,
            acquisition_method=acquisition_method,
            errors=(ExtractionError(code=code, message=message),),
        )


@dataclass(frozen=True, slots=True)
class InvoiceEnrichmentPatch:
    """Invoice fields returned by an optional semantic extractor."""

    fields: dict[str, ExtractedField]
    line_items: tuple[InvoiceLine, ...] | None = None
