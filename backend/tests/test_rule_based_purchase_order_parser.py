from datetime import date
from decimal import Decimal

from document_extractor.domain.common.enums import (
    DataExtractionMethod,
    ExtractionStatus,
)
from document_extractor.infrastructure.purchase_order.rule_based_parser import (  # noqa: E501
    RuleBasedPurchaseOrderParser,
)

_SPANISH_ORDER = """
PEDIDO DE COMPRA Nº PO-2026-0042
Fecha del pedido: 05/07/2026
Fecha prevista de entrega: 15/07/2026
Comprador: Zebra Retail SL
NIF comprador: B12345678
Proveedor: Suministros Norte SA
CIF proveedor: A87654321
Dirección de entrega: Calle Mayor 10, 28013 Madrid
Condiciones de pago: Transferencia a 30 días
SKU Descripción Cantidad Precio Total
MON-27 Monitor profesional 2 250,00 500,00
KEY-01 Teclado mecánico 3 50,00 150,00
Subtotal: 650,00 EUR
IVA 21%: 136,50 EUR
Total pedido: 786,50 EUR
"""


def test_extracts_a_complete_spanish_purchase_order() -> None:
    result = RuleBasedPurchaseOrderParser().parse(_SPANISH_ORDER)

    assert result.status is ExtractionStatus.COMPLETED
    assert result.data is not None
    assert result.data.order_number.value == "PO-2026-0042"
    assert result.data.issue_date.value == date(2026, 7, 5)
    assert result.data.expected_delivery_date.value == date(2026, 7, 15)
    assert result.data.buyer.name.value == "Zebra Retail SL"
    assert result.data.supplier.tax_id.value == "A87654321"
    assert result.data.shipping_address.value == "Calle Mayor 10, 28013 Madrid"
    assert result.data.payment_terms.value == "Transferencia a 30 días"
    assert result.data.total_amount.value == Decimal("786.50")
    assert result.data.currency.value == "EUR"
    assert len(result.data.line_items) == 2
    assert result.data.line_items[0].sku == "MON-27"
    assert result.data.line_items[0].line_total == Decimal("500.00")
    assert result.extraction_method is DataExtractionMethod.RULE_BASED


def test_understands_english_labels_and_flags_inconsistent_lines() -> None:
    result = RuleBasedPurchaseOrderParser().parse(
        """
        Purchase order: PO-99
        Order date: 2026-07-05
        Expected delivery date: 2026-07-20
        Buyer: Example Buyer Ltd
        Supplier: Example Supplier Ltd
        Ship to: 10 Main Street, London
        Payment terms: Net 30
        ABC-1 Office chair 2 100.00 250.00
        Order total: 250.00 GBP
        """
    )

    assert result.data is not None
    assert result.data.order_number.value == "PO-99"
    assert result.data.currency.value == "GBP"
    assert result.data.line_items[0].confidence == 0.58
    assert any("inconsistent" in warning for warning in result.warnings)
