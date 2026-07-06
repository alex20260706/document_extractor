"""Embedded PDF text acquisition using pdfplumber."""

from io import BytesIO

import pdfplumber
from pdfminer.pdfexceptions import PDFException

from document_extractor.domain.common.enums import ContentAcquisitionMethod
from document_extractor.domain.common.models import DocumentReadError


class PdfPlumberTextReader:
    """Read embedded text from PDF files with pdfplumber."""

    method = ContentAcquisitionMethod.EMBEDDED_TEXT

    @staticmethod
    def supports(filename: str, media_type: str) -> bool:
        """Accept files identified as PDF by name or media type.

        Args:
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            ``True`` when either identifier denotes a PDF.
        """

        return media_type == "application/pdf" or filename.lower().endswith(
            ".pdf"
        )

    @staticmethod
    def read(
        content: bytes,
        _filename: str,
        _media_type: str,
        /,
    ) -> str | None:
        """Return PDF text or None for image-only documents.

        Args:
            content: Raw PDF content.
            _filename: Unused filename required by the reader contract.
            _media_type: Unused MIME type from the reader contract.

        Returns:
            Embedded PDF text, or ``None`` for image-only documents.

        Raises:
            DocumentReadError: If the PDF is damaged or unreadable.
        """

        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                text = "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                ).strip()
        except (PDFException, OSError, ValueError) as error:
            raise DocumentReadError(
                "invalid_pdf",
                "The PDF is damaged or cannot be read.",
            ) from error
        return text or None
