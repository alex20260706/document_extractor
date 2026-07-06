"""Composition of document content readers."""

from document_extractor.domain.common.ports import DocumentContentReaderPort
from document_extractor.infrastructure.config import Settings
from document_extractor.infrastructure.readers.pdfplumber_reader import (
    PdfPlumberTextReader,
)
from document_extractor.infrastructure.readers.tesseract_ocr_reader import (
    TesseractOcrReader,
)


def build_content_readers(
    settings: Settings,
) -> tuple[DocumentContentReaderPort, ...]:
    """Build the content readers shared by document strategies.

    Args:
        settings: Runtime OCR configuration.

    Returns:
        Readers ordered from embedded text to OCR fallback.
    """

    return (
        PdfPlumberTextReader(),
        TesseractOcrReader(
            languages=settings.ocr_languages,
            dpi=settings.ocr_dpi,
            max_pages=settings.ocr_max_pages,
            max_pixels_per_page=settings.ocr_max_pixels_per_page,
            tesseract_cmd=settings.tesseract_cmd,
        ),
    )
