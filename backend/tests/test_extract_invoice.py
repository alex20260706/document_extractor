from document_extractor.application.invoice.extract_invoice import (
    ExtractInvoice,
)
from document_extractor.application.invoice.extract_invoice_command import (
    ExtractInvoiceCommand,
)
from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.domain.invoice.models import (
    InvoiceData,
    InvoiceEnrichmentPatch,
)
from document_extractor.infrastructure.invoice.rule_based_parser import (
    RuleBasedInvoiceParser,
)

_COMPLETE_INVOICE = """
Factura: F-2026-1
Fecha de emision: 02/07/2026
Emisor: Empresa Emisora SL
B12345678
Cliente: Empresa Cliente SL
X1234567L
Servicio profesional 1 100,00 100,00
Base imponible 100,00 EUR
IVA 21,00 EUR
Total 121,00 EUR
"""


class StubReader:
    def __init__(
        self,
        text: str | None,
        method: ContentAcquisitionMethod = (
            ContentAcquisitionMethod.EMBEDDED_TEXT
        ),
    ) -> None:
        self.text = text
        self.method = method

    def supports(self, filename: str, media_type: str) -> bool:
        return True

    def read(
        self,
        content: bytes,
        filename: str,
        media_type: str,
    ) -> str | None:
        return self.text


class StubEnricher:
    method = DataExtractionMethod.LLM

    def __init__(self, complete_data: InvoiceData) -> None:
        self.complete_data = complete_data
        self.calls = 0
        self.request: EnrichmentRequest | None = None

    def enrich(
        self,
        text: str,
        current_data: InvoiceData,
        request: EnrichmentRequest,
    ) -> InvoiceEnrichmentPatch:
        self.calls += 1
        self.request = request
        complete_fields = dict(self.complete_data.field_items())
        return InvoiceEnrichmentPatch(
            fields={
                name: complete_fields[name]
                for name in request.target_fields
                if name in complete_fields
            },
            line_items=self.complete_data.line_items,
        )


def _command() -> ExtractInvoiceCommand:
    return ExtractInvoiceCommand(
        content=b"document",
        filename="invoice.pdf",
        media_type="application/pdf",
    )


def test_does_not_call_llm_when_rules_are_complete() -> None:
    parser = RuleBasedInvoiceParser()
    complete = parser.parse(_COMPLETE_INVOICE).data
    assert complete is not None
    enricher = StubEnricher(complete)
    use_case = ExtractInvoice(
        readers=(StubReader(_COMPLETE_INVOICE),),
        parser=parser,
        enricher=enricher,
    )

    result = use_case.execute(_command())

    assert result.data is not None
    assert result.extraction_method is DataExtractionMethod.RULE_BASED
    assert enricher.calls == 0


def test_enriches_only_missing_or_weak_local_information() -> None:
    parser = RuleBasedInvoiceParser()
    complete = parser.parse(_COMPLETE_INVOICE).data
    assert complete is not None
    enricher = StubEnricher(complete)
    use_case = ExtractInvoice(
        readers=(StubReader("Factura: F-2026-1"),),
        parser=parser,
        enricher=enricher,
    )

    result = use_case.execute(_command())

    assert result.data is not None
    assert result.data.invoice_number.extraction_method is (
        DataExtractionMethod.RULE_BASED
    )
    assert result.data.total_amount.extraction_method is (
        DataExtractionMethod.LLM
    )
    assert result.extraction_method is DataExtractionMethod.HYBRID
    assert enricher.request is not None
    assert enricher.request.full_extraction is True


def test_keeps_partial_local_result_without_enricher() -> None:
    use_case = ExtractInvoice(
        readers=(StubReader("Factura: F-2026-1"),),
        parser=RuleBasedInvoiceParser(),
    )

    result = use_case.execute(_command())

    assert result.data is not None
    assert result.data.total_amount.missing is True


def test_requests_only_a_small_missing_field_patch() -> None:
    local_text = _COMPLETE_INVOICE.replace("IVA 21,00 EUR", "")
    complete = RuleBasedInvoiceParser().parse(_COMPLETE_INVOICE).data
    assert complete is not None
    enricher = StubEnricher(complete)
    use_case = ExtractInvoice(
        readers=(StubReader(local_text),),
        parser=RuleBasedInvoiceParser(),
        enricher=enricher,
    )

    result = use_case.execute(_command())

    assert result.data is not None
    assert enricher.request is not None
    assert enricher.request.full_extraction is False
    assert enricher.request.target_fields == ("tax_amount",)
    assert result.data.tax_amount.extraction_method is DataExtractionMethod.LLM


def test_tries_ocr_reader_after_pdf_has_no_embedded_text() -> None:
    use_case = ExtractInvoice(
        readers=(
            StubReader(None),
            StubReader(
                _COMPLETE_INVOICE,
                ContentAcquisitionMethod.OCR,
            ),
        ),
        parser=RuleBasedInvoiceParser(),
    )

    result = use_case.execute(_command())

    assert result.acquisition_method is ContentAcquisitionMethod.OCR


def test_fails_cleanly_when_no_reader_obtains_text() -> None:
    use_case = ExtractInvoice(
        readers=(StubReader(None),),
        parser=RuleBasedInvoiceParser(),
    )

    result = use_case.execute(_command())

    assert result.data is None
    assert result.errors[0].code == "content_unavailable"
