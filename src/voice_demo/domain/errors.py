from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DomainError(Exception):
    """
    Base class for domain-level errors. These should be mapped to HTTP or worker-level
    handling at the edges (API/Workers), not inside the domain.
    """
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class InvalidChunk(DomainError):
    def __init__(self, message: str = "Invalid transcript chunk", *, details: Optional[dict[str, Any]] = None):
        super().__init__("INVALID_CHUNK", message, details)


class OutOfOrderSeq(DomainError):
    def __init__(self, *, expected_next: int, got: int):
        super().__init__(
            "OUT_OF_ORDER_SEQ",
            "Transcript chunk sequence is out of order",
            {"expected_next": expected_next, "got": got},
        )


class DuplicateEvent(DomainError):
    def __init__(self, *, event_id: str):
        super().__init__(
            "DUPLICATE_EVENT",
            "Duplicate event_id received (idempotency)",
            {"event_id": event_id},
        )