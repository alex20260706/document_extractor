from document_extractor.application.common.acquire_content import (
    acquire_document_content,
)
from document_extractor.domain.common.enums import ContentAcquisitionMethod


class StubReader:
    def __init__(
        self,
        text: str | None,
        method: ContentAcquisitionMethod,
    ) -> None:
        self._text = text
        self.method = method

    def supports(self, filename: str, media_type: str) -> bool:
        return True

    def read(
        self,
        content: bytes,
        filename: str,
        media_type: str,
    ) -> str | None:
        return self._text


def test_tries_ocr_when_embedded_text_is_too_sparse() -> None:
    result = acquire_document_content(
        readers=(
            StubReader("1", ContentAcquisitionMethod.EMBEDDED_TEXT),
            StubReader(
                "Invoice F-2026-1 total amount 121 EUR",
                ContentAcquisitionMethod.OCR,
            ),
        ),
        content=b"document",
        filename="invoice.pdf",
        media_type="application/pdf",
    )

    assert result is not None
    assert result.acquisition_method is ContentAcquisitionMethod.OCR


def test_keeps_best_partial_text_when_no_reader_improves_it() -> None:
    result = acquire_document_content(
        readers=(
            StubReader("1", ContentAcquisitionMethod.EMBEDDED_TEXT),
            StubReader(None, ContentAcquisitionMethod.OCR),
        ),
        content=b"document",
        filename="invoice.pdf",
        media_type="application/pdf",
    )

    assert result is not None
    assert result.text == "1"
    assert result.acquisition_method is (
        ContentAcquisitionMethod.EMBEDDED_TEXT
    )
