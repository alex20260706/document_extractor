"""Confidence-aware merging of purchase-order enrichment."""

from dataclasses import replace

from document_extractor.domain.common.enums import DataExtractionMethod
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.domain.purchase_order.assessment import (
    LINE_ITEMS,
    RELIABLE_CONFIDENCE,
    assess_purchase_order,
    purchase_order_status,
    purchase_order_warnings,
)
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderData,
    PurchaseOrderEnrichmentPatch,
    PurchaseOrderExtractionResult,
    PurchaseOrderLine,
    PurchaseOrderParty,
)


def merge_purchase_order_patch(
    current: PurchaseOrderExtractionResult,
    patch: PurchaseOrderEnrichmentPatch,
    request: EnrichmentRequest,
) -> PurchaseOrderExtractionResult:
    """Apply reliable semantic values without degrading local data.

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
        existing = fields[name]
        if candidate.confidence < RELIABLE_CONFIDENCE:
            continue
        # Preserve local values when confidence is equal or better.
        if (
            not existing.missing
            and existing.confidence >= candidate.confidence
        ):
            continue
        fields[name] = replace(
            candidate, extraction_method=DataExtractionMethod.LLM
        )
        changed = True

    line_items = current.data.line_items
    # Line items are replaced as a complete, consistently reliable set.
    if (
        LINE_ITEMS in request.target_fields
        and patch.line_items
        and all(
            line.confidence >= RELIABLE_CONFIDENCE for line in patch.line_items
        )
        and _average_confidence(patch.line_items)
        > _average_confidence(line_items)
    ):
        line_items = tuple(
            replace(line, extraction_method=DataExtractionMethod.LLM)
            for line in patch.line_items
        )
        changed = True
    if not changed:
        return current

    data = PurchaseOrderData(
        order_number=fields["order_number"],
        issue_date=fields["issue_date"],
        expected_delivery_date=fields["expected_delivery_date"],
        buyer=PurchaseOrderParty(fields["buyer_name"], fields["buyer_tax_id"]),
        supplier=PurchaseOrderParty(
            fields["supplier_name"], fields["supplier_tax_id"]
        ),
        shipping_address=fields["shipping_address"],
        payment_terms=fields["payment_terms"],
        subtotal=fields["subtotal"],
        tax_amount=fields["tax_amount"],
        total_amount=fields["total_amount"],
        currency=fields["currency"],
        line_items=line_items,
    )
    assessment = assess_purchase_order(data)
    return PurchaseOrderExtractionResult(
        status=purchase_order_status(data, assessment),
        data=data,
        acquisition_method=current.acquisition_method,
        extraction_method=_result_method(data),
        warnings=purchase_order_warnings(data, assessment),
        errors=current.errors,
    )


def _average_confidence(lines: tuple[PurchaseOrderLine, ...]) -> float:
    """Calculate the mean confidence of purchase-order lines.

    Args:
        lines: Lines included in the calculation.

    Returns:
        Average confidence, or ``0`` when no lines are available.
    """
    return (
        sum(line.confidence for line in lines) / len(lines) if lines else 0.0
    )


def _result_method(data: PurchaseOrderData) -> DataExtractionMethod:
    """Determine the extraction method represented by merged data.

    Args:
        data: Final merged purchase-order data.

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
        if line.extraction_method
    )
    return (
        DataExtractionMethod.LLM
        if methods == {DataExtractionMethod.LLM}
        else DataExtractionMethod.HYBRID
    )
