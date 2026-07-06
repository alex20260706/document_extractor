"""Document-agnostic value objects used across extraction workflows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)

type FieldScalar = str | Decimal | date | int | bool


@dataclass(frozen=True, slots=True)
class ExtractedField:
    """A value extracted from a document with its confidence."""

    label: str
    value: FieldScalar | None = None
    confidence: float = 0.0
    extraction_method: DataExtractionMethod | None = None

    def __post_init__(self) -> None:
        """Validate the normalized confidence value.

        Raises:
            ValueError: If confidence falls outside the inclusive
                ``0`` to ``1`` range.
        """
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Field confidence must be between 0 and 1.")

    @property
    def missing(self) -> bool:
        """Return whether no usable value was extracted.

        Returns:
            ``True`` when the field has no value.
        """

        return self.value is None or self.value == ""


@dataclass(frozen=True, slots=True)
class ExtractionError:
    """A structured processing error suitable for API translation."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DocumentContent:
    """Readable text obtained from an uploaded document."""

    text: str
    acquisition_method: ContentAcquisitionMethod


@dataclass(frozen=True, slots=True)
class ExtractionAssessment:
    """Missing and uncertain parts detected in an extraction."""

    all_fields: tuple[str, ...]
    missing_fields: tuple[str, ...] = ()
    low_confidence_fields: tuple[str, ...] = ()

    @property
    def target_fields(self) -> tuple[str, ...]:
        """Return every field that may benefit from enrichment.

        Returns:
            Missing and low-confidence field names without duplicates.
        """

        return tuple(
            dict.fromkeys((*self.missing_fields, *self.low_confidence_fields))
        )

    @property
    def coverage(self) -> float:
        """Return the proportion of fields already present.

        Returns:
            A normalized coverage value between ``0`` and ``1``.
        """

        if not self.all_fields:
            return 1.0
        return 1 - len(self.missing_fields) / len(self.all_fields)

    @property
    def reliable_coverage(self) -> float:
        """Return the proportion of present, reliable fields.

        Returns:
            Normalized reliable coverage between ``0`` and ``1``.
        """

        if not self.all_fields:
            return 1.0
        unreliable = len(
            set((*self.missing_fields, *self.low_confidence_fields))
        )
        return 1 - unreliable / len(self.all_fields)


@dataclass(frozen=True, slots=True)
class EnrichmentRequest:
    """Fields an optional semantic extractor should process."""

    target_fields: tuple[str, ...]
    full_extraction: bool = False


class DocumentReadError(Exception):
    """Controlled failure while obtaining readable document content."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize a controlled document-reading failure.

        Args:
            code: Stable machine-readable error code.
            message: Human-readable error description.
        """
        super().__init__(message)
        self.code = code
        self.message = message
