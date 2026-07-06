"""Validated semantic enrichment for purchase-order extraction."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from document_extractor.domain.common.enums import DataExtractionMethod
from document_extractor.domain.common.models import (
    EnrichmentRequest,
    ExtractedField,
    FieldScalar,
)
from document_extractor.domain.common.ports import StructuredLlmClientPort
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderData,
    PurchaseOrderEnrichmentPatch,
    PurchaseOrderLine,
)
from document_extractor.infrastructure.purchase_order.purchase_order_enrichment_prompt import (  # noqa: E501
    PURCHASE_ORDER_INSTRUCTIONS,
    PURCHASE_ORDER_SCHEMA_NAME,
    build_purchase_order_input,
)

logger = logging.getLogger(__name__)


class _LlmField(BaseModel):
    """One purchase-order field returned by the LLM provider."""

    model_config = ConfigDict(extra="forbid")
    name: Literal[
        "order_number",
        "issue_date",
        "expected_delivery_date",
        "buyer_name",
        "buyer_tax_id",
        "supplier_name",
        "supplier_tax_id",
        "shipping_address",
        "payment_terms",
        "subtotal",
        "tax_amount",
        "total_amount",
        "currency",
    ]
    value: str | int | float | bool | None
    confidence: float = Field(ge=0.0, le=1.0)


class _LlmLine(BaseModel):
    """One purchase-order line returned by the LLM provider."""

    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1)
    sku: str | None
    quantity: str | int | float | None
    unit_price: str | int | float | None
    line_total: str | int | float | None
    confidence: float = Field(ge=0.0, le=1.0)


class _LlmPurchaseOrderPatch(BaseModel):
    """Validated structured response returned by the LLM provider."""

    model_config = ConfigDict(extra="forbid")
    fields: list[_LlmField]
    line_items: list[_LlmLine]


class PurchaseOrderLlmEnricher:
    """Turn purchase-order gaps into validated semantic patches."""

    method = DataExtractionMethod.LLM

    def __init__(
        self,
        client: StructuredLlmClientPort,
        max_input_characters: int = 60_000,
    ) -> None:
        """Initialize enrichment with a structured LLM client.

        Args:
            client: Provider-neutral structured-generation client.
            max_input_characters: Maximum document characters sent.
        """
        self._client = client
        self._max_input_characters = max_input_characters

    def enrich(
        self,
        text: str,
        current_data: PurchaseOrderData,
        request: EnrichmentRequest,
    ) -> PurchaseOrderEnrichmentPatch | None:
        """Request and validate unresolved purchase-order fields.

        Args:
            text: Readable purchase-order text.
            current_data: Values produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            A validated patch, or ``None`` on controlled failure.
        """
        try:
            response = self._client.generate_json(
                schema_name=PURCHASE_ORDER_SCHEMA_NAME,
                instructions=PURCHASE_ORDER_INSTRUCTIONS,
                input_text=build_purchase_order_input(
                    text, current_data, request, self._max_input_characters
                ),
                json_schema=_LlmPurchaseOrderPatch.model_json_schema(),
            )
            if response is None:
                return None
            parsed = _LlmPurchaseOrderPatch.model_validate(response)
            return self._to_patch(parsed, current_data, request)
        except (ValidationError, InvalidOperation, ValueError, TypeError):
            logger.warning(
                "Invalid structured purchase-order response from LLM",
                exc_info=True,
            )
            return None

    @staticmethod
    def _to_patch(
        response: _LlmPurchaseOrderPatch,
        current_data: PurchaseOrderData,
        request: EnrichmentRequest,
    ) -> PurchaseOrderEnrichmentPatch:
        """Convert a validated response to a domain patch.

        Args:
            response: Validated provider response.
            current_data: Values produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            A domain patch containing only requested fields.
        """
        current_fields = dict(current_data.field_items())
        candidates = {field.name: field for field in response.fields}
        fields = {}
        for name in request.target_fields:
            candidate = candidates.get(name)
            if candidate is None or name not in current_fields:
                continue
            fields[name] = ExtractedField(
                label=current_fields[name].label,
                value=_convert_value(name, candidate.value),
                confidence=candidate.confidence,
                extraction_method=DataExtractionMethod.LLM,
            )
        lines = None
        if "line_items" in request.target_fields and response.line_items:
            lines = tuple(
                PurchaseOrderLine(
                    description=line.description,
                    sku=line.sku,
                    quantity=_decimal(line.quantity),
                    unit_price=_decimal(line.unit_price),
                    line_total=_decimal(line.line_total),
                    confidence=line.confidence,
                    extraction_method=DataExtractionMethod.LLM,
                )
                for line in response.line_items
            )
        return PurchaseOrderEnrichmentPatch(fields=fields, line_items=lines)


def _convert_value(name: str, value: object) -> FieldScalar | None:
    """Convert a provider value to the expected domain scalar.

    Args:
        name: Target purchase-order field name.
        value: Untrusted provider value.

    Returns:
        A normalized domain value, or ``None`` for a null value.

    Raises:
        ValueError: If a date or currency value is unsupported.
        InvalidOperation: If a monetary value is not decimal.
    """
    if value is None:
        return None

    match name:
        case "issue_date" | "expected_delivery_date":
            return date.fromisoformat(str(value))
        case "subtotal" | "tax_amount" | "total_amount":
            return _decimal(value)
        case "currency":
            normalized = str(value).strip().upper()
            if normalized not in {"EUR", "USD", "GBP"}:
                raise ValueError("Unsupported purchase-order currency")
            return normalized
        case _:
            return str(value).strip() or None


def _decimal(value: object) -> Decimal | None:
    """Convert a provider value to a finite decimal.

    Args:
        value: Untrusted provider value.

    Returns:
        A finite decimal, or ``None`` for a null value.

    Raises:
        InvalidOperation: If the value is not decimal.
        ValueError: If the parsed decimal is not finite.
    """
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Non-finite decimal returned by LLM")
    return result
