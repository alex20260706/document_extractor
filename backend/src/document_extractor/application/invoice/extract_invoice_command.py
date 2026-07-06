"""Command accepted by the invoice extraction use case."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractInvoiceCommand:
    """Input required by the invoice-extraction use case."""

    content: bytes
    filename: str
    media_type: str
