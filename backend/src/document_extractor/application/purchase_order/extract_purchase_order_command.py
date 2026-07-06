"""Command accepted by the purchase-order extraction use case."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractPurchaseOrderCommand:
    """Input required by the purchase-order extraction use case."""

    content: bytes
    filename: str
    media_type: str
