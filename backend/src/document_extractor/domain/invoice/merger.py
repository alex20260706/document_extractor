"""Confidence-aware merging of semantic invoice enrichment."""

from dataclasses import replace

from document_extractor.domain.common.enums import DataExtractionMethod
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.domain.invoice.assessment import (
    RELIABLE_CONFIDENCE,
    assess_invoice,
    invoice_status,
    invoice_warnings,
)
from document_extractor.domain.invoice.models import (
    InvoiceData,
    InvoiceEnrichmentPatch,
    InvoiceExtractionResult,
    InvoiceLine,
    Party,
)


def merge_invoice_patch(
    current: InvoiceExtractionResult,
    patch: InvoiceEnrichmentPatch,
    request: EnrichmentRequest,
) -> InvoiceExtractionResult:
    """Apply LLM fields without replacing reliable local data.

    Args:
        current: Result produced by the local parser.
        patch: Candidate values from semantic enrichment.
        request: Fields authorized for enrichment.

    Returns:
        A reassessed result, or the original when the patch provides no
        reliable improvement.
    """

    if current.data is None:
        return current

    fields = dict(current.data.field_items())
    changed = False
    for name in request.target_fields:
        candidate = patch.fields.get(name)
        if name not in fields or candidate is None or candidate.missing:
            continue
        current_field = fields[name]
        if candidate.confidence < RELIABLE_CONFIDENCE:
            continue
        # Preserve local values when confidence is equal or better.
        if (
            not current_field.missing
            and current_field.confidence >= candidate.confidence
        ):
            continue
        fields[name] = replace(
            candidate,
            extraction_method=DataExtractionMethod.LLM,
        )
        changed = True

    line_items = current.data.line_items
    local_line_confidence = _average_line_confidence(line_items)
    patch_line_confidence = _average_line_confidence(patch.line_items or ())
    # Line items are replaced as a complete, consistently reliable set.
    if (
        "line_items" in request.target_fields
        and patch.line_items
        and all(
            line.confidence >= RELIABLE_CONFIDENCE for line in patch.line_items
        )
        and patch_line_confidence > local_line_confidence
    ):
        line_items = tuple(
            replace(line, extraction_method=DataExtractionMethod.LLM)
            for line in patch.line_items
        )
        changed = True

    if not changed:
        return current

    data = InvoiceData(
        invoice_number=fields["invoice_number"],
        issue_date=fields["issue_date"],
        issuer=Party(
            name=fields["issuer_name"],
            tax_id=fields["issuer_tax_id"],
        ),
        receiver=Party(
            name=fields["receiver_name"],
            tax_id=fields["receiver_tax_id"],
        ),
        taxable_base=fields["taxable_base"],
        tax_amount=fields["tax_amount"],
        total_amount=fields["total_amount"],
        currency=fields["currency"],
        line_items=line_items,
    )
    assessment = assess_invoice(data)
    return InvoiceExtractionResult(
        status=invoice_status(data, assessment),
        data=data,
        acquisition_method=current.acquisition_method,
        extraction_method=_result_method(data),
        warnings=invoice_warnings(data, assessment),
        errors=current.errors,
    )


def _average_line_confidence(
    line_items: tuple[InvoiceLine, ...],
) -> float:
    """Calculate the average confidence of the line items.

    Args:
        line_items: Lines included in the calculation.

    Returns:
        Average confidence, or ``0`` when no lines are available.
    """

    if not line_items:
        return 0.0
    return sum(line.confidence for line in line_items) / len(line_items)


def _result_method(
    data: InvoiceData,
) -> DataExtractionMethod:
    """Determine the extraction method for the result.

    Args:
        data: Final merged invoice data.

    Returns:
        ``LLM`` when all values are semantic; otherwise ``HYBRID``.
    """

    methods = {
        field.extraction_method
        for _, field in data.field_items()
        if not field.missing and field.extraction_method is not None
    }
    methods.update(
        line.extraction_method
        for line in data.line_items
        if line.extraction_method is not None
    )
    return (
        DataExtractionMethod.LLM
        if methods == {DataExtractionMethod.LLM}
        else DataExtractionMethod.HYBRID
    )
