"""API response schemas for invoice extraction."""

from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
    DocumentKind,
    ExtractionStatus,
)
from document_extractor.domain.invoice.models import InvoiceExtractionResult


class FieldResponse(BaseModel):
    """Extracted field exposed by the API."""

    label: str
    value: str | Decimal | date | int | bool | None
    confidence: float = Field(ge=0, le=1)
    missing: bool
    extraction_method: DataExtractionMethod | None


class InvoiceLineResponse(BaseModel):
    """Extracted invoice line exposed by the API."""

    description: str
    quantity: Decimal | None
    unit_price: Decimal | None
    line_total: Decimal | None
    confidence: float = Field(ge=0, le=1)
    extraction_method: DataExtractionMethod | None


class ProcessingErrorResponse(BaseModel):
    """Controlled processing error exposed by the API."""

    code: str
    message: str


class InvoiceExtractionResponse(BaseModel):
    """API representation of an invoice extraction result."""

    status: ExtractionStatus
    document_type: DocumentKind = DocumentKind.INVOICE
    acquisition_method: ContentAcquisitionMethod | None
    extraction_method: DataExtractionMethod | None
    fields: dict[str, FieldResponse]
    line_items: list[InvoiceLineResponse]
    warnings: list[str]
    errors: list[ProcessingErrorResponse]

    @classmethod
    def from_domain(
        cls,
        extraction: InvoiceExtractionResult,
    ) -> Self:
        """Map a domain invoice result to its API representation.

        Args:
            extraction: Domain invoice extraction result.

        Returns:
            The serializable invoice response.
        """
        data = extraction.data
        return cls(
            status=extraction.status,
            document_type=extraction.document_kind,
            acquisition_method=extraction.acquisition_method,
            extraction_method=extraction.extraction_method,
            fields={
                name: FieldResponse(
                    label=item.label,
                    value=item.value,
                    confidence=item.confidence,
                    missing=item.missing,
                    extraction_method=item.extraction_method,
                )
                for name, item in (data.field_items() if data else ())
            },
            line_items=[
                InvoiceLineResponse(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    confidence=item.confidence,
                    extraction_method=item.extraction_method,
                )
                for item in (data.line_items if data else ())
            ],
            warnings=list(extraction.warnings),
            errors=[
                ProcessingErrorResponse(code=error.code, message=error.message)
                for error in extraction.errors
            ],
        )
