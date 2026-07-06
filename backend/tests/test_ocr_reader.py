from io import BytesIO

import pytest
from PIL import Image

from document_extractor.domain.common.enums import ContentAcquisitionMethod
from document_extractor.domain.common.models import DocumentReadError
from document_extractor.infrastructure.readers.tesseract_ocr_reader import (
    TesseractOcrReader,
)


def test_reads_text_from_an_image(monkeypatch) -> None:
    image_bytes = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image_bytes, format="PNG")

    invocation = {}

    def recognize(image, lang, config):
        invocation.update(image=image, lang=lang, config=config)
        return "Factura F-1"

    monkeypatch.setattr(
        "pytesseract.image_to_string",
        recognize,
    )
    reader = TesseractOcrReader()

    text = reader.read(image_bytes.getvalue(), "invoice.png", "image/png")

    assert reader.method is ContentAcquisitionMethod.OCR
    assert text == "Factura F-1"
    assert invocation["image"].mode == "L"
    assert invocation["image"].width == 1800
    assert invocation["lang"] == "spa+eng"
    assert invocation["config"] == (
        "--oem 3 --psm 4 -c preserve_interword_spaces=1"
    )


def test_supports_pdf_and_common_image_formats() -> None:
    reader = TesseractOcrReader()

    assert reader.supports("invoice.pdf", "application/pdf")
    assert reader.supports("invoice.jpg", "image/jpeg")
    assert not reader.supports("invoice.docx", "application/octet-stream")


def test_rejects_images_over_the_pixel_limit() -> None:
    image_bytes = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image_bytes, format="PNG")
    reader = TesseractOcrReader(max_pixels_per_page=100)

    with pytest.raises(DocumentReadError) as captured:
        reader.read(image_bytes.getvalue(), "invoice.png", "image/png")

    assert captured.value.code == "document_too_large"
