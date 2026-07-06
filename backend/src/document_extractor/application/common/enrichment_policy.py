"""Policy for deciding when semantic enrichment is required."""

from document_extractor.domain.common.models import (
    EnrichmentRequest,
    ExtractionAssessment,
)

FULL_EXTRACTION_THRESHOLD = 0.5


def decide_enrichment(
    assessment: ExtractionAssessment,
    full_extraction_threshold: float = FULL_EXTRACTION_THRESHOLD,
) -> EnrichmentRequest | None:
    """Choose a field patch or full semantic extraction when needed.

    Args:
        assessment: Quality assessment of the local extraction.
        full_extraction_threshold: Reliable coverage below which every
            field is requested from the semantic extractor.

    Returns:
        A targeted or full enrichment request, or ``None`` when all
        fields are reliable.
    """

    if not assessment.target_fields:
        return None
    full_extraction = assessment.reliable_coverage < full_extraction_threshold
    return EnrichmentRequest(
        target_fields=(
            assessment.all_fields
            if full_extraction
            else assessment.target_fields
        ),
        full_extraction=full_extraction,
    )
