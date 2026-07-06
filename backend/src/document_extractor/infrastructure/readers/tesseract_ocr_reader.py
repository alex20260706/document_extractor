"""OCR text acquisition for scanned PDFs and supported images."""

from collections.abc import Generator, Iterator
from contextlib import closing, contextmanager
from io import BytesIO
from math import ceil

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageSequence, UnidentifiedImageError
from pytesseract import TesseractError, TesseractNotFoundError

from document_extractor.domain.common.enums import ContentAcquisitionMethod
from document_extractor.domain.common.models import DocumentReadError
from document_extractor.infrastructure.readers.ocr_image_preprocessor import (
    prepare_image_for_ocr,
    prepared_image_size,
)

_IMAGE_MEDIA_TYPES = {
    "image/bmp",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
_IMAGE_EXTENSIONS = (
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
)


class TesseractOcrReader:
    """Obtain text from scanned PDFs and images using local OCR."""

    method = ContentAcquisitionMethod.OCR

    def __init__(
        self,
        languages: str = "spa+eng",
        dpi: int = 300,
        max_pages: int = 20,
        max_pixels_per_page: int = 40_000_000,
        tesseract_cmd: str | None = None,
    ) -> None:
        """Initialize the Tesseract OCR reader.

        Args:
            languages: Tesseract language codes joined by ``+``.
            dpi: Resolution used to render PDF pages.
            max_pages: Maximum accepted pages or image frames.
            max_pixels_per_page: Maximum accepted pixels per page.
            tesseract_cmd: Optional path to the Tesseract executable.
        """

        self._languages = languages
        self._dpi = dpi
        self._max_pages = max_pages
        self._max_pixels_per_page = max_pixels_per_page
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @staticmethod
    def supports(filename: str, media_type: str) -> bool:
        """Accept PDFs and configured image formats.

        Args:
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            ``True`` for PDFs and configured image formats.
        """

        name = filename.lower()
        return (
            media_type == "application/pdf"
            or media_type in _IMAGE_MEDIA_TYPES
            or name.endswith((".pdf", *_IMAGE_EXTENSIONS))
        )

    def read(
        self,
        content: bytes,
        filename: str,
        media_type: str,
        /,
    ) -> str | None:
        """Render pages, run Tesseract and join non-empty page texts.

        Args:
            content: Raw PDF or image content.
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            Joined OCR text, or ``None`` when no text is recognized.

        Raises:
            DocumentReadError: If OCR is unavailable, the document is
                invalid, or configured safety limits are exceeded.
        """

        try:
            images = (
                self._pdf_images(content)
                if media_type == "application/pdf"
                or filename.lower().endswith(".pdf")
                else self._image_frames(content)
            )
            with closing(images):
                page_texts = [self._recognize(image) for image in images]
            text = "\n\n".join(page_texts).strip()
        except DocumentReadError:
            raise
        except TesseractNotFoundError as error:
            raise DocumentReadError(
                "ocr_unavailable",
                "Tesseract OCR is not installed or configured.",
            ) from error
        except TesseractError as error:
            raise DocumentReadError(
                "ocr_failed",
                "Tesseract could not recognize the document content.",
            ) from error
        except Image.DecompressionBombError as error:
            raise DocumentReadError(
                "document_too_large",
                "The image exceeds Pillow's safe decompression limit.",
            ) from error
        except (
            UnidentifiedImageError,
            pdfium.PdfiumError,
            OSError,
            ValueError,
        ) as error:
            raise DocumentReadError(
                "invalid_document",
                "The document is damaged or cannot be read.",
            ) from error
        return text or None

    def _recognize(self, image: Image.Image) -> str:
        """Prepare and recognize one page with bounded memory.

        Args:
            image: One rendered page or image frame.

        Returns:
            Recognized text with surrounding whitespace removed.

        Raises:
            DocumentReadError: If the original or prepared image exceeds
                the configured pixel limit.
        """

        self._ensure_safe_size(image.size)
        self._ensure_safe_size(prepared_image_size(image.size))
        prepared = prepare_image_for_ocr(image)
        try:
            self._ensure_safe_size(prepared.size)
            return pytesseract.image_to_string(
                prepared,
                lang=self._languages,
                config="--oem 3 --psm 4 -c preserve_interword_spaces=1",
            ).strip()
        finally:
            prepared.close()

    def _pdf_images(
        self,
        content: bytes,
    ) -> Generator[Image.Image, None, None]:
        """Render PDF pages lazily so only one image is retained.

        Args:
            content: Raw PDF content.

        Yields:
            One rendered page image at a time.

        Raises:
            DocumentReadError: If page count or size exceeds a limit.
        """
        with pdfium.PdfDocument(content) as document:
            self._ensure_safe_page_count(len(document))
            scale = self._dpi / 72
            for page_number in range(len(document)):
                with self._render_page(
                    document,
                    page_number,
                    scale,
                ) as image:
                    yield image

    @contextmanager
    def _render_page(
        self,
        document: pdfium.PdfDocument,
        page_number: int,
        scale: float,
    ) -> Iterator[Image.Image]:
        """Render one checked page and close all its resources.

        Args:
            document: Open PDF document.
            page_number: Zero-based page index.
            scale: PDF rendering scale.

        Yields:
            The rendered Pillow image.

        Raises:
            DocumentReadError: If the rendered dimensions are unsafe.
        """

        with closing(document[page_number]) as page:
            width, height = page.get_size()
            self._ensure_safe_size((ceil(width * scale), ceil(height * scale)))
            with closing(page.render(scale=scale)) as bitmap:
                image = bitmap.to_pil()
                try:
                    yield image
                finally:
                    image.close()

    def _image_frames(
        self,
        content: bytes,
    ) -> Generator[Image.Image, None, None]:
        """Extract image frames lazily.

        Args:
            content: Raw image content.

        Yields:
            One RGB image frame at a time.

        Raises:
            DocumentReadError: If frame count or size exceeds a limit.
        """
        with Image.open(BytesIO(content)) as image:
            self._ensure_safe_page_count(getattr(image, "n_frames", 1))
            for frame in ImageSequence.Iterator(image):
                self._ensure_safe_size(frame.size)
                converted = frame.convert("RGB")
                try:
                    yield converted
                finally:
                    converted.close()

    def _ensure_safe_page_count(self, page_count: int) -> None:
        """Reject documents exceeding the configured OCR page limit.

        Args:
            page_count: Number of document pages or image frames.

        Raises:
            DocumentReadError: If the page count exceeds the limit.
        """
        if page_count > self._max_pages:
            raise DocumentReadError(
                "document_too_large",
                f"The document exceeds the {self._max_pages}-page OCR limit.",
            )

    def _ensure_safe_size(self, size: tuple[int, int]) -> None:
        """Reject invalid or excessively large image dimensions.

        Args:
            size: Image width and height.

        Raises:
            DocumentReadError: If dimensions are invalid or exceed the
                configured pixel limit.
        """
        width, height = size
        if width <= 0 or height <= 0:
            raise DocumentReadError(
                "invalid_document",
                "The document contains an invalid page size.",
            )
        if width * height > self._max_pixels_per_page:
            raise DocumentReadError(
                "document_too_large",
                "A document page exceeds the OCR pixel limit.",
            )
