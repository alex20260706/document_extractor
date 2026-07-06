from document_extractor.presentation.common.file_signatures import (
    has_expected_file_signature,
)


def test_accepts_every_supported_file_signature() -> None:
    valid_files = {
        "application/pdf": b"%PDF-1.7\n",
        "image/bmp": b"BMcontent",
        "image/jpeg": b"\xff\xd8\xff\xe0content",
        "image/png": b"\x89PNG\r\n\x1a\ncontent",
        "image/tiff": b"II*\x00content",
        "image/webp": b"RIFF\x04\x00\x00\x00WEBPcontent",
    }

    assert all(
        has_expected_file_signature(content, media_type)
        for media_type, content in valid_files.items()
    )
    assert has_expected_file_signature(b"MM\x00*content", "image/tiff")


def test_rejects_missing_mismatched_and_incomplete_file_signatures() -> None:
    assert not has_expected_file_signature(b"not a pdf", "application/pdf")
    assert not has_expected_file_signature(b"%PDF-1.7", "image/png")
    assert not has_expected_file_signature(b"RIFFshort", "image/webp")
    assert not has_expected_file_signature(b"content", "application/zip")
