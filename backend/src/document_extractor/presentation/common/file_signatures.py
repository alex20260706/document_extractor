"""File-signature checks for supported upload media types."""

_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/bmp": (b"BM",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
}


def has_expected_file_signature(content: bytes, media_type: str) -> bool:
    """Check whether file bytes match the declared supported media type.

    Args:
        content: Raw uploaded file bytes.
        media_type: Media type declared by the upload.

    Returns:
        ``True`` when the expected format signature is present.
    """

    if media_type == "image/webp":
        return (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )

    return any(
        content.startswith(signature)
        for signature in _SIGNATURES.get(media_type, ())
    )
