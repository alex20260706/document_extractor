"""Generic strategy contract and registry for document extraction."""

from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel

from document_extractor.domain.common.enums import DocumentKind


class DocumentExtractionStrategy(Protocol):
    """HTTP-facing strategy for one supported document type."""

    document_kind: DocumentKind

    def execute(
        self,
        content: bytes,
        filename: str,
        media_type: str,
    ) -> BaseModel:
        """Extract one document and return its API response.

        Args:
            content: Raw document content.
            filename: Original document filename.
            media_type: Declared MIME type of the document.

        Returns:
            The document-specific API response model.
        """

        ...


class ExtractionStrategyRegistry:
    """Resolve the extraction strategy selected by the user."""

    def __init__(
        self,
        strategies: Iterable[DocumentExtractionStrategy],
    ) -> None:
        """Index enabled strategies by document kind.

        Args:
            strategies: Enabled extraction strategies.
        """
        self._strategies = {
            strategy.document_kind: strategy for strategy in strategies
        }

    def get(
        self,
        document_kind: DocumentKind,
    ) -> DocumentExtractionStrategy | None:
        """Resolve an enabled document strategy.

        Args:
            document_kind: Requested business document type.

        Returns:
            The matching strategy, or ``None`` when not enabled.
        """

        return self._strategies.get(document_kind)
