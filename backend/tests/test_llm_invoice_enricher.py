import json

from document_extractor.domain.common.enums import DataExtractionMethod
from document_extractor.domain.common.models import EnrichmentRequest
from document_extractor.infrastructure.invoice.llm_invoice_enricher import (
    InvoiceLlmEnricher,
)
from document_extractor.infrastructure.invoice.rule_based_parser import (
    RuleBasedInvoiceParser,
)


class FakeStructuredClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.input_text = ""
        self.instructions = ""

    def generate_json(
        self,
        schema_name: str,
        instructions: str,
        input_text: str,
        json_schema: dict[str, object],
    ) -> dict[str, object]:
        self.input_text = input_text
        self.instructions = instructions
        assert schema_name == "invoice_enrichment"
        assert instructions
        assert json_schema["type"] == "object"
        return self.response


def test_requests_and_returns_only_target_invoice_fields() -> None:
    current = RuleBasedInvoiceParser().parse("Factura F-1").data
    assert current is not None
    client = FakeStructuredClient(
        {
            "fields": [
                {
                    "name": "total_amount",
                    "value": "121.00",
                    "confidence": 0.91,
                },
                {
                    "name": "currency",
                    "value": "EUR",
                    "confidence": 0.95,
                },
            ],
            "line_items": [],
        }
    )
    enricher = InvoiceLlmEnricher(client)

    patch = enricher.enrich(
        "Factura F-1 Total 121 EUR",
        current,
        EnrichmentRequest(target_fields=("total_amount",)),
    )

    assert patch is not None
    assert set(patch.fields) == {"total_amount"}
    assert str(patch.fields["total_amount"].value) == "121.00"
    assert patch.fields["total_amount"].extraction_method is (
        DataExtractionMethod.LLM
    )
    assert json.loads(client.input_text)["target_fields"] == ["total_amount"]
    assert "untrusted invoice content" in client.instructions
    assert "total_amount" in json.loads(client.input_text)["field_definitions"]
