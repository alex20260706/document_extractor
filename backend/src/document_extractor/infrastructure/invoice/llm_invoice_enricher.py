"""Validated semantic enrichment for invoice extraction."""

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
from document_extractor.domain.invoice.models import (
    InvoiceData,
    InvoiceEnrichmentPatch,
    InvoiceLine,
)

from .invoice_enrichment_prompt import (
    INVOICE_ENRICHMENT_INSTRUCTIONS,
    INVOICE_ENRICHMENT_SCHEMA_NAME,
    build_invoice_enrichment_input,
)

logger = logging.getLogger(__name__)


class _LlmField(BaseModel):
    """A field extracted from an invoice by an LLM."""

    model_config = ConfigDict(extra="forbid")

    name: Literal[
        "invoice_number",
        "issue_date",
        "issuer_name",
        "issuer_tax_id",
        "receiver_name",
        "receiver_tax_id",
        "taxable_base",
        "tax_amount",
        "total_amount",
        "currency",
    ]
    value: str | int | float | bool | None = Field(
        description="Extracted value, or null when unsupported by the text.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence based only on explicit document evidence.",
    )


class _LlmLine(BaseModel):
    """A line extracted from an invoice by an LLM."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    quantity: str | int | float | None
    unit_price: str | int | float | None
    line_total: str | int | float | None
    confidence: float = Field(ge=0.0, le=1.0)


class _LlmInvoicePatch(BaseModel):
    """Validated structured response returned by the LLM provider."""

    model_config = ConfigDict(extra="forbid")

    fields: list[_LlmField]
    line_items: list[_LlmLine]


class InvoiceLlmEnricher:
    """Turn invoice gaps into a provider-neutral LLM request."""

    method = DataExtractionMethod.LLM

    def __init__(
        self,
        client: StructuredLlmClientPort,
        max_input_characters: int = 60_000,
    ) -> None:
        """Initialize invoice enrichment with a structured LLM client.

        Args:
            client: Provider-neutral structured-generation client.
            max_input_characters: Maximum document characters sent.
        """
        self._client = client
        self._max_input_characters = max_input_characters

    def enrich(
        self,
        text: str,
        current_data: InvoiceData,
        request: EnrichmentRequest,
    ) -> InvoiceEnrichmentPatch | None:
        """Request only weak fields and validate the returned patch.

        Args:
            text: Readable invoice text.
            current_data: Values produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            A validated patch, or ``None`` on controlled failure.
        """

        input_text = build_invoice_enrichment_input(
            text=text,
            current_data=current_data,
            request=request,
            max_input_characters=self._max_input_characters,
        )
        try:
            response = self._client.generate_json(
                schema_name=INVOICE_ENRICHMENT_SCHEMA_NAME,
                instructions=INVOICE_ENRICHMENT_INSTRUCTIONS,
                input_text=input_text,
                json_schema=_LlmInvoicePatch.model_json_schema(),
            )
            if response is None:
                return None
            parsed = _LlmInvoicePatch.model_validate(response)
            return self._to_patch(parsed, current_data, request)
        except (ValidationError, InvalidOperation, ValueError, TypeError):
            logger.warning(
                "Invalid structured invoice response from LLM",
                exc_info=True,
            )
            return None

    @staticmethod
    def _to_patch(
        response: _LlmInvoicePatch,
        current_data: InvoiceData,
        request: EnrichmentRequest,
    ) -> InvoiceEnrichmentPatch:
        """Convert the LLM response to an enrichment patch.

        Args:
            response: Validated provider response.
            current_data: Values produced by the local parser.
            request: Fields selected for semantic enrichment.

        Returns:
            A domain patch containing only requested fields.
        """

        current_fields = dict(current_data.field_items())
        response_fields = {
            candidate.name: candidate for candidate in response.fields
        }
        fields: dict[str, ExtractedField] = {}
        for name in request.target_fields:
            candidate = response_fields.get(name)
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
                InvoiceLine(
                    description=line.description,
                    quantity=_decimal_or_none(line.quantity),
                    unit_price=_decimal_or_none(line.unit_price),
                    line_total=_decimal_or_none(line.line_total),
                    confidence=line.confidence,
                    extraction_method=DataExtractionMethod.LLM,
                )
                for line in response.line_items
            )
        return InvoiceEnrichmentPatch(fields=fields, line_items=lines)


def _convert_value(name: str, value: object) -> FieldScalar | None:
    """Convert a provider value to the expected domain scalar.

    Args:
        name: Target invoice field name.
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
        case "issue_date":
            return date.fromisoformat(str(value))
        case "taxable_base" | "tax_amount" | "total_amount":
            return _decimal_or_none(value)
        case "currency":
            normalized = str(value).strip().upper()
            if normalized not in {"EUR", "USD", "GBP"}:
                raise ValueError("Unsupported invoice currency")
            return normalized
        case _:
            return str(value).strip() or None


def _decimal_or_none(value: object) -> Decimal | None:
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
