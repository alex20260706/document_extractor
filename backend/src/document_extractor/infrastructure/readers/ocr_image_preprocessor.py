"""Image preprocessing shared by OCR document readers."""

from PIL import Image, ImageFilter, ImageOps

_MIN_DOCUMENT_WIDTH = 1800


def prepared_image_size(size: tuple[int, int]) -> tuple[int, int]:
    """Calculate the dimensions preprocessing will produce.

    Args:
        size: Original image width and height.

    Returns:
        Upscaled dimensions, or the original size when wide enough.
    """

    width, height = size
    if width >= _MIN_DOCUMENT_WIDTH:
        return size
    scale = _MIN_DOCUMENT_WIDTH / width
    return _MIN_DOCUMENT_WIDTH, round(height * scale)


def prepare_image_for_ocr(image: Image.Image) -> Image.Image:
    """Improve document legibility while preserving its aspect ratio.

    Args:
        image: Source document image.

    Returns:
        A grayscale, resized and sharpened copy ready for OCR.
    """

    prepared = ImageOps.grayscale(image)
    if prepared.width < _MIN_DOCUMENT_WIDTH:
        prepared = prepared.resize(
            prepared_image_size(prepared.size),
            Image.Resampling.LANCZOS,
        )

    prepared = ImageOps.autocontrast(prepared, cutoff=1)
    return prepared.filter(
        ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3)
    )
