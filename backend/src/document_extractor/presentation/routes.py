"""HTTP routes exposed by the document-extraction API."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from document_extractor.presentation.common.controller import (
    DocumentExtractionController,
)
from document_extractor.presentation.common.schemas import ErrorResponse
from document_extractor.presentation.composition import (
    get_extraction_controller,
)
from document_extractor.presentation.invoice.schemas import (
    InvoiceExtractionResponse,
)
from document_extractor.presentation.purchase_order.schemas import (
    PurchaseOrderExtractionResponse,
)

ExtractionResponse = (
    InvoiceExtractionResponse | PurchaseOrderExtractionResponse
)

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report whether the API process is available.

    Returns:
        A minimal healthy status payload.
    """

    return {"status": "ok"}


@router.post(
    "/extractions",
    response_model=ExtractionResponse,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["extractions"],
)
async def extract_document(
    file: Annotated[
        UploadFile,
        File(description="PDF or image document"),
    ],
    document_type: Annotated[str, Form()],
    controller: Annotated[
        DocumentExtractionController,
        Depends(get_extraction_controller),
    ],
) -> ExtractionResponse:
    """Validate and extract one explicitly typed document.

    Args:
        file: Uploaded PDF or image document.
        document_type: Document strategy selected by the user.
        controller: Configured extraction controller dependency.

    Returns:
        The document-specific extraction response.

    Raises:
        HTTPException: If the upload or document type is invalid.
        TypeError: If a strategy returns an unsupported response model.
    """

    response = await controller.extract(file, document_type)

    if isinstance(
        response,
        (
            InvoiceExtractionResponse,
            PurchaseOrderExtractionResponse,
        ),
    ):
        return response

    raise TypeError(
        "Extraction strategy returned an unsupported response model"
    )
