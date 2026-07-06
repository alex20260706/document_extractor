import pytest
from pdfminer.pdfparser import PDFSyntaxError

from document_extractor.domain.common.models import DocumentReadError
from document_extractor.infrastructure.readers.pdfplumber_reader import (
    PdfPlumberTextReader,
)


class StubPage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class StubPdf:
    def __init__(self, pages: list[StubPage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


def test_separates_text_from_different_pdf_pages(monkeypatch) -> None:
    monkeypatch.setattr(
        "pdfplumber.open",
        lambda source: StubPdf([StubPage("Page one"), StubPage("Page two")]),
    )

    text = PdfPlumberTextReader.read(
        b"pdf",
        "invoice.pdf",
        "application/pdf",
    )

    assert text == "Page one\n\nPage two"


def test_translates_pdf_syntax_errors(monkeypatch) -> None:
    def fail_to_open(source):
        raise PDFSyntaxError("invalid")

    monkeypatch.setattr("pdfplumber.open", fail_to_open)

    with pytest.raises(DocumentReadError) as captured:
        PdfPlumberTextReader.read(
            b"invalid",
            "invoice.pdf",
            "application/pdf",
        )

    assert captured.value.code == "invalid_pdf"
