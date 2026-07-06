from decimal import Decimal

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
    ExtractionStatus,
)
from document_extractor.domain.common.models import ExtractedField
from document_extractor.infrastructure.invoice.rule_based_parser import (
    RuleBasedInvoiceParser,
)


def test_extracts_main_fields_and_line_items() -> None:
    text = """
    FACTURA: FAC-2026-001
    Fecha de emision: 01/07/2026
    Emisor: Zebra Servicios SL
    B12345678
    Cliente: Acme Iberia SL
    ESX1234567X
    Consultoria tecnica 2 100,00 200,00
    Base imponible 200,00 EUR
    IVA 42,00 EUR
    Total factura 242,00 EUR
    """

    result = RuleBasedInvoiceParser().parse(text)
    assert result.data is not None

    assert result.data.invoice_number.value == "FAC-2026-001"
    assert result.data.total_amount.value == Decimal("242.00")
    assert result.data.issuer.name.value == "Zebra Servicios SL"
    assert result.data.receiver.name.value == "Acme Iberia SL"
    assert result.data.currency.value == "EUR"
    assert result.data.line_items[0].description == "Consultoria tecnica"
    assert result.acquisition_method is ContentAcquisitionMethod.EMBEDDED_TEXT
    assert result.extraction_method is DataExtractionMethod.RULE_BASED
    assert result.status in (
        ExtractionStatus.COMPLETED,
        ExtractionStatus.PARTIAL,
    )


def test_marks_unknown_fields_as_missing() -> None:
    result = RuleBasedInvoiceParser().parse("Factura TEST-1")
    assert result.data is not None

    assert result.status is ExtractionStatus.PARTIAL
    assert result.data.total_amount.missing is True
    assert result.warnings


def test_rejects_invalid_confidence() -> None:
    try:
        ExtractedField(label="Total", value=Decimal("10"), confidence=1.1)
    except ValueError as error:
        assert "between 0 and 1" in str(error)
    else:
        raise AssertionError("Invalid confidence was accepted")


def test_does_not_confuse_total_with_invoice_number() -> None:
    result = RuleBasedInvoiceParser().parse("Factura total 242,00 EUR")
    assert result.data is not None

    assert result.data.invoice_number.missing is True
    assert result.data.total_amount.value == Decimal("242.00")


def test_associates_tax_ids_with_nearest_party() -> None:
    text = """
    Cliente: Comprador SL
    B11111111
    Proveedor: Vendedor SL
    A22222222
    Factura Nº: F-2026-2
    Total: 121,00 EUR
    """

    result = RuleBasedInvoiceParser().parse(text)
    assert result.data is not None

    assert result.data.issuer.tax_id.value == "A22222222"
    assert result.data.receiver.tax_id.value == "B11111111"


def test_accepts_iso_dates_english_amounts_and_flexible_lines() -> None:
    text = """
    Invoice No.: INV_2026-77
    Issue date: 2026-07-02
    Supplier: Example Services SL
    B12345678
    Customer: Example Customer SL
    X1234567L
    Premium service 2 x 617.28 21% 1,234.56 USD
    Net amount: USD 1,234.56
    VAT 21%: USD 259.26
    Grand total: USD 1,493.82
    """

    result = RuleBasedInvoiceParser().parse(text)
    assert result.data is not None

    assert result.data.issue_date.value.isoformat() == "2026-07-02"
    assert result.data.total_amount.value == Decimal("1493.82")
    assert result.data.currency.value == "USD"
    assert result.data.line_items[0].line_total == Decimal("1234.56")


def test_accepts_ocr_spacing_currency_symbols_and_parentheses() -> None:
    text = """
    Factura numero: F-2026-90
    Fecha de emisión: 03 / 07 / 2026
    Base imponible: € 1 234,56
    IVA (21%): 259,26 €
    Total a pagar: (1.493,82) €
    """

    result = RuleBasedInvoiceParser().parse(text)
    assert result.data is not None

    assert result.data.issue_date.value.isoformat() == "2026-07-03"
    assert result.data.taxable_base.value == Decimal("1234.56")
    assert result.data.tax_amount.value == Decimal("259.26")
    assert result.data.total_amount.value == Decimal("-1493.82")
    assert result.data.currency.value == "EUR"


def test_accepts_spaced_tax_ids_and_lowercase_line_descriptions() -> None:
    text = """
    Proveedor: Zebra Servicios SL
    ES B-12345678
    Cliente: Acme Iberia SL
    X 1234567 L
    maintenance 24x7 2 x 617.28 21% 1,234.56 USD
    """

    result = RuleBasedInvoiceParser().parse(text)
    assert result.data is not None

    assert result.data.issuer.tax_id.value == "ESB12345678"
    assert result.data.receiver.tax_id.value == "X1234567L"
    assert result.data.line_items[0].description == "maintenance 24x7"
    assert result.data.line_items[0].line_total == Decimal("1234.56")
