"""Quality assessment and outcome rules for extracted invoices."""

from document_extractor.domain.common.enums import ExtractionStatus
from document_extractor.domain.common.models import ExtractionAssessment
from document_extractor.domain.invoice.models import InvoiceData

_LINE_ITEMS = "line_items"
RELIABLE_CONFIDENCE = 0.6
_ESSENTIAL_FIELDS = ("invoice_number", "total_amount")
_MAX_MISSING_FIELDS_FOR_COMPLETED = 2


def assess_invoice(
    data: InvoiceData,
    confidence_threshold: float = RELIABLE_CONFIDENCE,
) -> ExtractionAssessment:
    """Identify missing and low-confidence invoice information.

    Args:
        data: Structured invoice data to assess.
        confidence_threshold: Minimum confidence considered reliable.

    Returns:
        Missing and low-confidence invoice fields.
    """

    fields = dict(data.field_items())
    all_fields = (*fields.keys(), _LINE_ITEMS)
    missing = [name for name, field in fields.items() if field.missing]
    low_confidence = [
        name
        for name, field in fields.items()
        if not field.missing and field.confidence < confidence_threshold
    ]

    if not data.line_items:
        missing.append(_LINE_ITEMS)
    elif any(
        line.confidence < confidence_threshold for line in data.line_items
    ):
        low_confidence.append(_LINE_ITEMS)

    return ExtractionAssessment(
        all_fields=all_fields,
        missing_fields=tuple(missing),
        low_confidence_fields=tuple(low_confidence),
    )


def invoice_status(
    data: InvoiceData,
    assessment: ExtractionAssessment,
) -> ExtractionStatus:
    """Classify a usable invoice as completed or partial.

    Args:
        data: Structured invoice data.
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


def invoice_warnings(
    data: InvoiceData,
    assessment: ExtractionAssessment,
) -> tuple[str, ...]:
    """Build human-readable review warnings for an invoice.

    Args:
        data: Structured invoice data.
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
    if _LINE_ITEMS in assessment.missing_fields:
        warnings.append(
            "No invoice line items were detected with enough confidence."
        )
    elif _LINE_ITEMS in assessment.low_confidence_fields:
        warnings.append(
            "Review invoice line items: some amounts are inconsistent."
        )
    return tuple(warnings)
