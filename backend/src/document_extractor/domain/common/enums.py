"""Enums shared by every supported document type."""

from enum import StrEnum


class ExtractionStatus(StrEnum):
    """Overall outcome of a document extraction."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class DocumentKind(StrEnum):
    """Business type assigned to a document."""

    INVOICE = "invoice"
    DELIVERY_NOTE = "delivery_note"
    PURCHASE_ORDER = "purchase_order"
    WORK_REPORT = "work_report"
    MAINTENANCE_REPORT = "maintenance_report"


class ContentAcquisitionMethod(StrEnum):
    """Method used to turn a document into readable content."""

    EMBEDDED_TEXT = "embedded_text"
    OCR = "ocr"


class DataExtractionMethod(StrEnum):
    """Method that converted content into structured business data."""

    RULE_BASED = "rule_based"
    LLM = "llm"
    HYBRID = "hybrid"
