import json

from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.infrastructure.purchase_order.llm_purchase_order_enricher import (  # noqa: E501
    PurchaseOrderLlmEnricher,
)
from document_extractor.infrastructure.purchase_order.rule_based_parser import (  # noqa: E501
    RuleBasedPurchaseOrderParser,
)


class FakeStructuredClient:
    def __init__(self) -> None:
        self.input_text = ""

    def generate_json(
        self,
        schema_name: str,
        instructions: str,
        input_text: str,
        json_schema: dict[str, object],
    ) -> dict[str, object]:
        assert schema_name == "purchase_order_enrichment"
        assert "untrusted purchase-order content" in instructions
        assert json_schema["type"] == "object"
        self.input_text = input_text
        return {
            "fields": [
                {
                    "name": "payment_terms",
                    "value": "Net 30",
                    "confidence": 0.9,
                },
                {"name": "currency", "value": "EUR", "confidence": 0.9},
            ],
            "line_items": [],
        }


def test_requests_only_target_purchase_order_fields() -> None:
    current = RuleBasedPurchaseOrderParser().parse("Purchase order PO-1").data
    assert current is not None
    client = FakeStructuredClient()

    patch = PurchaseOrderLlmEnricher(client).enrich(
        "Purchase order PO-1 Payment terms Net 30",
        current,
        EnrichmentRequest(target_fields=("payment_terms",)),
    )

    assert patch is not None
    assert set(patch.fields) == {"payment_terms"}
    assert json.loads(client.input_text)["target_fields"] == ["payment_terms"]
