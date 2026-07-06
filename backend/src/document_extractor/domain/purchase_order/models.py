"""Domain models for purchase-order extraction."""

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
class PurchaseOrderParty:
    """A buyer or supplier named in a purchase order."""

    name: ExtractedField
    tax_id: ExtractedField


@dataclass(frozen=True, slots=True)
class PurchaseOrderLine:
    """One product or service requested by the buyer."""

    description: str
    sku: str | None = None
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
class PurchaseOrderData:
    """Structured business data extracted from a purchase order."""

    order_number: ExtractedField
    issue_date: ExtractedField
    expected_delivery_date: ExtractedField
    buyer: PurchaseOrderParty
    supplier: PurchaseOrderParty
    shipping_address: ExtractedField
    payment_terms: ExtractedField
    subtotal: ExtractedField
    tax_amount: ExtractedField
    total_amount: ExtractedField
    currency: ExtractedField
    line_items: tuple[PurchaseOrderLine, ...] = ()

    def field_items(self) -> tuple[tuple[str, ExtractedField], ...]:
        """Expose header fields in a stable API-friendly order.

        Returns:
            Field names and values in presentation order.
        """
        return (
            ("order_number", self.order_number),
            ("issue_date", self.issue_date),
            ("expected_delivery_date", self.expected_delivery_date),
            ("buyer_name", self.buyer.name),
            ("buyer_tax_id", self.buyer.tax_id),
            ("supplier_name", self.supplier.name),
            ("supplier_tax_id", self.supplier.tax_id),
            ("shipping_address", self.shipping_address),
            ("payment_terms", self.payment_terms),
            ("subtotal", self.subtotal),
            ("tax_amount", self.tax_amount),
            ("total_amount", self.total_amount),
            ("currency", self.currency),
        )


@dataclass(frozen=True, slots=True)
class PurchaseOrderExtractionResult:
    """Normalized outcome of extracting a purchase order."""

    status: ExtractionStatus
    data: PurchaseOrderData | None
    acquisition_method: ContentAcquisitionMethod | None = None
    extraction_method: DataExtractionMethod | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[ExtractionError, ...] = ()

    @property
    def document_kind(self) -> DocumentKind:
        """Identify the extracted document type.

        Returns:
            The purchase-order document kind.
        """
        return DocumentKind.PURCHASE_ORDER

    @classmethod
    def failed(
        cls,
        code: str,
        message: str,
        acquisition_method: ContentAcquisitionMethod | None = None,
    ) -> Self:
        """Build a failed result with one processing error.

        Args:
            code: Stable machine-readable error code.
            message: Human-readable error description.
            acquisition_method: Document reading method, if known.

        Returns:
            A failed purchase-order extraction result.
        """
        return cls(
            status=ExtractionStatus.FAILED,
            data=None,
            acquisition_method=acquisition_method,
            errors=(ExtractionError(code=code, message=message),),
        )


@dataclass(frozen=True, slots=True)
class PurchaseOrderEnrichmentPatch:
    """Purchase-order values returned by semantic enrichment."""

    fields: dict[str, ExtractedField]
    line_items: tuple[PurchaseOrderLine, ...] | None = None
