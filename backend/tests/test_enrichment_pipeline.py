from dataclasses import replace
from decimal import Decimal

from document_extractor.application.common.enrichment_policy import (
    decide_enrichment,
)
from document_extractor.domain.common.enums import DataExtractionMethod
from document_extractor.domain.common.models import (
    EnrichmentRequest,
    ExtractedField,
    ExtractionAssessment,
)
from document_extractor.domain.invoice.merger import merge_invoice_patch
from document_extractor.domain.invoice.models import InvoiceEnrichmentPatch
from document_extractor.infrastructure.invoice.rule_based_parser import (
    RuleBasedInvoiceParser,
)

_INVOICE = """
Invoice F-1
Issue date: 2026-07-04
Supplier: Seller SL
B12345678
Customer: Buyer SL
X1234567L
Service 1 100.00 100.00
Subtotal 100.00 EUR
VAT 21.00 EUR
Total 121.00 EUR
"""


def test_full_enrichment_uses_reliable_coverage() -> None:
    assessment = ExtractionAssessment(
        all_fields=("a", "b", "c", "d", "e"),
        missing_fields=("a",),
        low_confidence_fields=("b", "c"),
    )

    request = decide_enrichment(assessment)

    assert request is not None
    assert request.full_extraction is True
    assert request.target_fields == assessment.all_fields


def test_merge_rejects_an_llm_value_worse_than_local_value() -> None:
    current = RuleBasedInvoiceParser().parse(_INVOICE)
    assert current.data is not None
    weak_total = ExtractedField(
        label="Total",
        value=Decimal("121.00"),
        confidence=0.58,
        extraction_method=DataExtractionMethod.RULE_BASED,
    )
    current = replace(
        current,
        data=replace(current.data, total_amount=weak_total),
    )
    patch = InvoiceEnrichmentPatch(
        fields={
            "total_amount": replace(
                weak_total,
                value=Decimal("999.00"),
                confidence=0.5,
                extraction_method=DataExtractionMethod.LLM,
            )
        }
    )

    merged = merge_invoice_patch(
        current,
        patch,
        EnrichmentRequest(target_fields=("total_amount",)),
    )

    assert merged.data is not None
    assert merged.data.total_amount.value == Decimal("121.00")
    assert merged.extraction_method is DataExtractionMethod.RULE_BASED


def test_merge_accepts_a_more_reliable_llm_value() -> None:
    current = RuleBasedInvoiceParser().parse(_INVOICE)
    assert current.data is not None
    missing_total = ExtractedField(label="Total")
    current = replace(
        current,
        data=replace(current.data, total_amount=missing_total),
    )
    patch = InvoiceEnrichmentPatch(
        fields={
            "total_amount": ExtractedField(
                label="Total",
                value=Decimal("121.00"),
                confidence=0.9,
                extraction_method=DataExtractionMethod.LLM,
            )
        }
    )

    merged = merge_invoice_patch(
        current,
        patch,
        EnrichmentRequest(target_fields=("total_amount",)),
    )

    assert merged.data is not None
    assert merged.data.total_amount.value == Decimal("121.00")
    assert merged.extraction_method is DataExtractionMethod.HYBRID
