import logging
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from document_extractor.main import app
from document_extractor.presentation.composition import (
    get_extraction_controller,
)

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_non_pdf() -> None:
    response = client.post(
        "/api/extractions",
        files={"file": ("invoice.txt", b"not a pdf", "text/plain")},
        data={"document_type": "invoice"},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_file"


def test_rejects_content_that_does_not_match_the_declared_type() -> None:
    response = client.post(
        "/api/extractions",
        files={"file": ("invoice.pdf", b"not a pdf", "application/pdf")},
        data={"document_type": "invoice"},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == {
        "code": "invalid_file_content",
        "message": "The file content does not match its declared type.",
    }


def test_requires_an_explicit_document_type() -> None:
    response = client.post(
        "/api/extractions",
        files={"file": ("invoice.pdf", b"pdf", "application/pdf")},
    )

    assert response.status_code == 422


def test_rejects_a_known_but_unavailable_document_type() -> None:
    response = client.post(
        "/api/extractions",
        files={"file": ("document.pdf", b"pdf", "application/pdf")},
        data={"document_type": "delivery_note"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_document_type"


def test_rejects_an_unknown_document_type() -> None:
    response = client.post(
        "/api/extractions",
        files={"file": ("document.pdf", b"pdf", "application/pdf")},
        data={"document_type": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unknown_document_type"


def test_extracts_invoice_sample_through_shared_endpoint() -> None:
    sample = (
        Path(__file__).parents[2] / "samples" / "invoice-modern-spanish.pdf"
    )

    response = client.post(
        "/api/extractions",
        files={
            "file": (
                sample.name,
                sample.read_bytes(),
                "application/pdf",
            )
        },
        data={"document_type": "invoice"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_type"] == "invoice"
    assert body["status"] == "completed"
    assert body["fields"]["invoice_number"]["value"] == "FAC-2026-101"
    assert body["fields"]["total_amount"]["value"] == "3025.00"
    assert len(body["line_items"]) == 3


def test_extracts_purchase_order_sample_through_shared_endpoint() -> None:
    sample = (
        Path(__file__).parents[2]
        / "samples"
        / "purchase-order-industrial-spanish.pdf"
    )

    response = client.post(
        "/api/extractions",
        files={
            "file": (
                sample.name,
                sample.read_bytes(),
                "application/pdf",
            )
        },
        data={"document_type": "purchase_order"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_type"] == "purchase_order"
    assert body["status"] == "completed"
    assert body["fields"]["order_number"]["value"] == "PO-ES-4408"
    assert body["fields"]["total_amount"]["value"] == "1464.10"
    assert len(body["line_items"]) == 3


def test_translates_unexpected_errors_to_a_safe_json_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_controller_dependency() -> None:
        raise RuntimeError("Sensitive technical detail")

    app.dependency_overrides[get_extraction_controller] = (
        fail_controller_dependency
    )
    error_client = TestClient(app, raise_server_exceptions=False)

    try:
        with caplog.at_level(logging.ERROR, logger="document_extractor.main"):
            response = error_client.post(
                "/api/extractions",
                files={
                    "file": (
                        "invoice.pdf",
                        b"%PDF-1.4",
                        "application/pdf",
                    )
                },
                data={"document_type": "invoice"},
            )
    finally:
        app.dependency_overrides.pop(get_extraction_controller, None)

    assert response.status_code == 500
    detail = response.json()["detail"]
    correlation_id = detail["correlation_id"]
    assert detail == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "correlation_id": correlation_id,
    }
    assert response.headers["X-Correlation-ID"] == correlation_id
    assert UUID(correlation_id)
    assert "Sensitive technical detail" not in response.text
    assert correlation_id in caplog.text
    assert "Sensitive technical detail" in caplog.text
