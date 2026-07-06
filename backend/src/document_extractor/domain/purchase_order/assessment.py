"""Quality assessment and outcome rules for purchase orders."""

from document_extractor.domain.common.enums import ExtractionStatus
from document_extractor.domain.common.models import ExtractionAssessment
from document_extractor.domain.purchase_order.models import PurchaseOrderData

LINE_ITEMS = "line_items"
RELIABLE_CONFIDENCE = 0.6
_ESSENTIAL_FIELDS = (
    "order_number",
    "buyer_name",
    "supplier_name",
    "total_amount",
)
_MAX_MISSING_FIELDS_FOR_COMPLETED = 3


def assess_purchase_order(
    data: PurchaseOrderData,
    confidence_threshold: float = RELIABLE_CONFIDENCE,
) -> ExtractionAssessment:
    """Identify missing and low-confidence purchase-order information.

    Args:
        data: Structured purchase-order data to assess.
        confidence_threshold: Minimum confidence considered reliable.

    Returns:
        Missing and low-confidence purchase-order fields.
    """
    fields = dict(data.field_items())
    missing = [name for name, field in fields.items() if field.missing]
    low_confidence = [
        name
        for name, field in fields.items()
        if not field.missing and field.confidence < confidence_threshold
    ]
    if not data.line_items:
        missing.append(LINE_ITEMS)
    elif any(
        line.confidence < confidence_threshold for line in data.line_items
    ):
        low_confidence.append(LINE_ITEMS)
    return ExtractionAssessment(
        all_fields=(*fields, LINE_ITEMS),
        missing_fields=tuple(missing),
        low_confidence_fields=tuple(low_confidence),
    )


def purchase_order_status(
    data: PurchaseOrderData, assessment: ExtractionAssessment
) -> ExtractionStatus:
    """Classify a usable purchase order as completed or partial.

    Args:
        data: Structured purchase-order data.
        assessment: Quality assessment of that data.

    Returns:
        ``COMPLETED`` when the business acceptance rules are met;
        otherwise ``PARTIAL``.
    """
    fields = dict(data.field_items())
    essential_found = all(
        not fields[name].missing for name in _ESSENTIAL_FIELDS
    )
    return (
        ExtractionStatus.COMPLETED
        if essential_found
        and len(assessment.missing_fields) <= _MAX_MISSING_FIELDS_FOR_COMPLETED
        and not assessment.low_confidence_fields
        and bool(data.line_items)
        else ExtractionStatus.PARTIAL
    )


def purchase_order_warnings(
    data: PurchaseOrderData, assessment: ExtractionAssessment
) -> tuple[str, ...]:
    """Build review warnings for a purchase-order result.

    Args:
        data: Structured purchase-order data.
        assessment: Quality assessment of that data.

    Returns:
        Human-readable warnings for fields requiring review.
    """
    fields = dict(data.field_items())
    warnings = [
        f"Field not found: {fields[name].label}."
        for name in assessment.missing_fields
        if name in fields
    ]
    warnings.extend(
        f"Review {fields[name].label}: low confidence."
        for name in assessment.low_confidence_fields
        if name in fields
    )
    if LINE_ITEMS in assessment.missing_fields:
        warnings.append(
            "No purchase order line items were detected with enough "
            "confidence."
        )
    elif LINE_ITEMS in assessment.low_confidence_fields:
        warnings.append(
            "Review purchase order line items: some amounts are inconsistent."
        )
    return tuple(warnings)
