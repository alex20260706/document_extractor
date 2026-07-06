"""Upload validation and document-strategy dispatch."""

from typing import Never

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from document_extractor.domain.common.enums import DocumentKind
from document_extractor.presentation.common.file_signatures import (
    has_expected_file_signature,
)
from document_extractor.presentation.common.strategies import (
    ExtractionStrategyRegistry,
)

_ALLOWED_FILES = {
    "application/pdf": (".pdf",),
    "image/bmp": (".bmp",),
    "image/jpeg": (".jpeg", ".jpg"),
    "image/png": (".png",),
    "image/tiff": (".tif", ".tiff"),
    "image/webp": (".webp",),
}


class DocumentExtractionController:
    """Validate uploads and dispatch them to a document strategy."""

    def __init__(
        self,
        strategies: ExtractionStrategyRegistry,
        max_upload_bytes: int,
    ) -> None:
        """Initialize upload validation and strategy dispatch.

        Args:
            strategies: Registry of enabled document strategies.
            max_upload_bytes: Maximum accepted upload size in bytes.
        """
        self._strategies = strategies
        self._max_upload_bytes = max_upload_bytes

    async def extract(
        self,
        file: UploadFile,
        document_type: str,
    ) -> BaseModel:
        """Process one upload with the explicitly selected strategy.

        Args:
            file: Uploaded document.
            document_type: User-selected document type value.

        Returns:
            The document-specific API response model.

        Raises:
            HTTPException: If the type, file format, content or size is
                invalid.
        """

        try:
            document_kind = DocumentKind(document_type)
        except ValueError:
            self._reject(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "unknown_document_type",
                "The selected document type is not recognized.",
            )

        strategy = self._strategies.get(document_kind)
        if strategy is None:
            self._reject(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "unsupported_document_type",
                "The selected document type is not available yet.",
            )

        filename = (file.filename or "").lower()
        extensions = _ALLOWED_FILES.get(file.content_type or "")
        if extensions is None or not filename.endswith(extensions):
            self._reject(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "unsupported_file",
                "The file must be a supported PDF or image.",
            )

        content = await file.read(self._max_upload_bytes + 1)
        await file.close()
        if not content:
            self._reject(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "empty_file",
                "The uploaded file is empty.",
            )
        if len(content) > self._max_upload_bytes:
            self._reject(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "file_too_large",
                "The file exceeds the allowed size.",
            )
        if not has_expected_file_signature(
            content,
            file.content_type or "",
        ):
            self._reject(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "invalid_file_content",
                "The file content does not match its declared type.",
            )

        return await run_in_threadpool(
            strategy.execute,
            content,
            file.filename or "document",
            file.content_type or "application/octet-stream",
        )

    @staticmethod
    def _reject(status_code: int, code: str, message: str) -> Never:
        """Raise a structured HTTP validation error.

        Args:
            status_code: HTTP status returned to the client.
            code: Stable machine-readable error code.
            message: Human-readable error description.

        Raises:
            HTTPException: Always, with the structured error detail.
        """
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": message},
        )
