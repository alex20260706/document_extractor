"""FastAPI application bootstrap."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from document_extractor.infrastructure.config import get_settings
from document_extractor.presentation.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def handle_unexpected_exception(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a safe error response and retain diagnostics in logs.

    Args:
        request: Request that failed.
        exception: Unhandled application exception.

    Returns:
        A stable JSON error with a correlation identifier.
    """

    correlation_id = str(uuid4())
    logger.error(
        "Unexpected request failure: correlation_id=%s method=%s path=%s",
        correlation_id,
        request.method,
        request.url.path,
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
                "correlation_id": correlation_id,
            }
        },
        headers={"X-Correlation-ID": correlation_id},
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        The configured application instance.
    """
    settings = get_settings()

    logger.info(
        "Application configured: llm_enabled=%s, llm_model=%s",
        settings.llm_enabled,
        settings.llm_model,
    )

    app = FastAPI(
        title="Zebra Document Extractor API",
        version="0.1.0",
        description="Temporary, non-persistent document data extraction.",
    )
    app.add_exception_handler(Exception, handle_unexpected_exception)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(router)
    return app


app = create_app()
