from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from .constants import Route
from .errors import InvalidChunk
from .time_utils import utcnow


@dataclass(frozen=True)
class TranscriptChunk:
    """
    Represents a single incremental transcript chunk (like streaming STT output).
    """
    call_id: str
    seq: int
    ts: datetime
    text: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "stt"
    schema_version: int = 1

    def validate(self) -> None:
        if not self.call_id or not isinstance(self.call_id, str):
            raise InvalidChunk("call_id must be a non-empty string")
        if not isinstance(self.seq, int) or self.seq < 0:
            raise InvalidChunk("seq must be a non-negative integer", details={"seq": self.seq})
        if not isinstance(self.text, str):
            raise InvalidChunk("text must be a string")
        # keep it conservative; you can adjust later
        if len(self.text) > 2000:
            raise InvalidChunk("text too large", details={"max_len": 2000, "got_len": len(self.text)})
        if self.schema_version != 1:
            raise InvalidChunk("unsupported schema_version", details={"schema_version": self.schema_version})


@dataclass(frozen=True)
class Suggestion:
    """
    Represents a suggested next agent response, or guidance.
    """
    call_id: str
    based_on_seq: int
    suggested_reply: str
    rationale: str = ""
    confidence: float = 0.5
    ts: datetime = field(default_factory=utcnow)
    schema_version: int = 1

    def validate(self) -> None:
        if not self.call_id:
            raise ValueError("call_id required")
        if not isinstance(self.based_on_seq, int) or self.based_on_seq < 0:
            raise ValueError("based_on_seq must be non-negative int")
        if not self.suggested_reply or not isinstance(self.suggested_reply, str):
            raise ValueError("suggested_reply required")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Score:
    """
    Represents real-time call quality scoring output.
    """
    call_id: str
    score: int  # 0-100
    tags: list[str]
    coaching_note: str = ""
    ts: datetime = field(default_factory=utcnow)
    schema_version: int = 1

    def validate(self) -> None:
        if not self.call_id:
            raise ValueError("call_id required")
        if not isinstance(self.score, int) or not (0 <= self.score <= 100):
            raise ValueError("score must be int 0..100")
        if not isinstance(self.tags, list):
            raise ValueError("tags must be a list[str]")


@dataclass(frozen=True)
class RouteDecision:
    call_id: str
    route: Route = Route.UNKNOWN
    confidence: float = 0.5
    reason: str = ""
    based_on_seq: int = 0
    ts: datetime = field(default_factory=utcnow)
    schema_version: int = 1

    def validate(self) -> None:
        if not isinstance(self.route, Route):
            raise ValueError("route must be a Route enum")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class CallSession:
    """
    In-memory representation of a call session state. In production, state is typically
    stored in a fast store (Redis) and reconstructed as needed.
    """
    call_id: str
    last_seq: int = -1
    recent_chunks: list[TranscriptChunk] = field(default_factory=list)
    rolling_summary: str = ""
    latest_suggestion: Optional[Suggestion] = None
    latest_score: Optional[Score] = None
    latest_route: Optional[RouteDecision] = None
    latest_trace_id: Optional[str] = None

    def apply_chunk(self, chunk: TranscriptChunk, *, max_chunks: int = 20) -> None:
        """
        Apply a chunk to session state (purely in-memory). Ordering/idempotency
        enforcement will live in the application layer, but we keep this helper
        for clarity and tests.
        """
        self.last_seq = max(self.last_seq, chunk.seq)
        self.recent_chunks.append(chunk)
        if len(self.recent_chunks) > max_chunks:
            self.recent_chunks = self.recent_chunks[-max_chunks:]

    def transcript_text(self) -> str:
        return " ".join(c.text for c in self.recent_chunks if c.text).strip()