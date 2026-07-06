"""Shared HTTP response schemas."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Machine-readable API error detail."""

    code: str
    message: str
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope returned by FastAPI."""

    detail: ErrorDetail
