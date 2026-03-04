from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from voice_demo.domain.errors import DomainError, OutOfOrderSeq, DuplicateEvent, InvalidChunk


def domain_error_to_response(_: Request, exc: DomainError) -> JSONResponse:
    # Default mapping
    status = 400

    if isinstance(exc, InvalidChunk):
        status = 422
    elif isinstance(exc, OutOfOrderSeq):
        status = 409
    elif isinstance(exc, DuplicateEvent):
        # Idempotency: treat duplicates as success-ish
        status = 202

    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details or {},
            }
        },
    )
