"""API response schemas for purchase-order extraction."""

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
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderExtractionResult,
)


class FieldResponse(BaseModel):
    """Extracted field exposed by the API."""

    label: str
    value: str | Decimal | date | int | bool | None
    confidence: float = Field(ge=0, le=1)
    missing: bool
    extraction_method: DataExtractionMethod | None


class ProcessingErrorResponse(BaseModel):
    """Controlled processing error exposed by the API."""

    code: str
    message: str


class PurchaseOrderLineResponse(BaseModel):
    """Extracted purchase-order line exposed by the API."""

    description: str
    sku: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    line_total: Decimal | None
    confidence: float = Field(ge=0, le=1)
    extraction_method: DataExtractionMethod | None


class PurchaseOrderExtractionResponse(BaseModel):
    """API representation of a purchase-order extraction result."""

    status: ExtractionStatus
    document_type: DocumentKind = DocumentKind.PURCHASE_ORDER
    acquisition_method: ContentAcquisitionMethod | None
    extraction_method: DataExtractionMethod | None
    fields: dict[str, FieldResponse]
    line_items: list[PurchaseOrderLineResponse]
    warnings: list[str]
    errors: list[ProcessingErrorResponse]

    @classmethod
    def from_domain(cls, extraction: PurchaseOrderExtractionResult) -> Self:
        """Map a domain purchase-order result to its API representation.

        Args:
            extraction: Domain purchase-order extraction result.

        Returns:
            The serializable purchase-order response.
        """
        data = extraction.data
        return cls(
            status=extraction.status,
            document_type=extraction.document_kind,
            acquisition_method=extraction.acquisition_method,
            extraction_method=extraction.extraction_method,
            fields={
                name: FieldResponse(
                    label=field.label,
                    value=field.value,
                    confidence=field.confidence,
                    missing=field.missing,
                    extraction_method=field.extraction_method,
                )
                for name, field in (data.field_items() if data else ())
            },
            line_items=[
                PurchaseOrderLineResponse(
                    description=line.description,
                    sku=line.sku,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_total=line.line_total,
                    confidence=line.confidence,
                    extraction_method=line.extraction_method,
                )
                for line in (data.line_items if data else ())
            ],
            warnings=list(extraction.warnings),
            errors=[
                ProcessingErrorResponse(code=error.code, message=error.message)
                for error in extraction.errors
            ],
        )
