"""Document-agnostic ports implemented by infrastructure adapters."""

from typing import Protocol

from document_extractor.domain.common.enums import ContentAcquisitionMethod


class DocumentContentReaderPort(Protocol):
    """Contract for turning supported files into readable text."""

    method: ContentAcquisitionMethod

    def supports(
        self,
        filename: str,
        media_type: str,
    ) -> bool:
        """Return whether this reader understands the file format.

        Args:
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            ``True`` when the reader accepts the file format.
        """

        ...

    def read(
        self,
        content: bytes,
        filename: str,
        media_type: str,
        /,
    ) -> str | None:
        """Return readable text or None when the file has no text.

        Args:
            content: Raw document content.
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            Extracted text, or ``None`` when no text is available.
        """

        ...


class StructuredLlmClientPort(Protocol):
    """Contract for asking any LLM provider for structured JSON."""

    def generate_json(
        self,
        schema_name: str,
        instructions: str,
        input_text: str,
        json_schema: dict[str, object],
    ) -> dict[str, object] | None:
        """Return structured JSON or None on controlled failure.

        Args:
            schema_name: The name identifying the response schema.
            instructions: The instructions for the LLM.
            input_text: The input text for the LLM.
            json_schema: The JSON schema for the LLM.

        Returns:
            Parsed JSON, or ``None`` on a controlled provider failure.
        """
        ...
