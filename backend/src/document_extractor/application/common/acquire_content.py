"""Document-agnostic content acquisition across configured readers."""

import re
from collections.abc import Sequence

from document_extractor.domain.common.models import DocumentContent
from document_extractor.domain.common.ports import DocumentContentReaderPort

_MIN_ALPHANUMERIC_CHARACTERS = 10
_MIN_WORDS = 2


def acquire_document_content(
    readers: Sequence[DocumentContentReaderPort],
    content: bytes,
    filename: str,
    media_type: str,
) -> DocumentContent | None:
    """Acquire text from the first reader that returns usable content.

    Readers are evaluated in priority order. If none reaches the quality
    threshold, the strongest partial extraction is returned.

    Args:
        readers: Content readers in evaluation order.
        content: Raw document content.
        filename: Original document filename.
        media_type: Declared MIME type of the document.

    Returns:
        The first usable extraction, the strongest partial extraction,
        or ``None`` when no reader produces text.
    """

    best_candidate: DocumentContent | None = None
    best_score = (0, 0)

    for reader in readers:
        if not reader.supports(filename, media_type):
            continue
        text = reader.read(content, filename, media_type)
        if not text:
            continue

        candidate = DocumentContent(
            text=text,
            acquisition_method=reader.method,
        )
        score = _text_score(text)
        # Preserve a fallback when every reader produces sparse content.
        if score > best_score:
            best_candidate = candidate
            best_score = score
        if _is_meaningful_text(score):
            return candidate

    return best_candidate


def _text_score(text: str) -> tuple[int, int]:
    """Calculate a document-agnostic text quality score.

    Args:
        text: Extracted document text.

    Returns:
        The alphanumeric character count and the word count.
    """

    alphanumeric_count = sum(character.isalnum() for character in text)
    word_count = len(re.findall(r"\w{2,}", text, flags=re.UNICODE))
    return alphanumeric_count, word_count


def _is_meaningful_text(score: tuple[int, int]) -> bool:
    """Determine whether a text score meets the quality threshold.

    Args:
        score: Alphanumeric character and word counts.

    Returns:
        ``True`` when both minimum quality requirements are met.
    """

    alphanumeric_count, word_count = score
    return (
        alphanumeric_count >= _MIN_ALPHANUMERIC_CHARACTERS
        and word_count >= _MIN_WORDS
    )
