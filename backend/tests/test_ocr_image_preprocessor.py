from PIL import Image

from document_extractor.infrastructure.readers.ocr_image_preprocessor import (
    prepare_image_for_ocr,
    prepared_image_size,
)


def test_prepares_low_resolution_document_for_ocr() -> None:
    image = Image.new("RGB", (900, 1200), "white")

    prepared = prepare_image_for_ocr(image)

    assert prepared.mode == "L"
    assert prepared.size == (1800, 2400)
    assert image.size == (900, 1200)


def test_does_not_enlarge_high_resolution_document() -> None:
    image = Image.new("RGB", (2400, 3200), "white")

    prepared = prepare_image_for_ocr(image)

    assert prepared.size == image.size


def test_predicts_upscaled_size_before_allocating_the_image() -> None:
    assert prepared_image_size((900, 1200)) == (1800, 2400)
