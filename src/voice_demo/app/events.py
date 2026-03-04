from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from voice_demo.domain.constants import Route
import uuid


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str | None = None
    schema_version: int = 1


class TranscriptChunkEvent(BaseEvent):
    call_id: str
    seq: int
    ts: datetime
    text: str
    source: str = "stt"


class SuggestionEvent(BaseEvent):
    call_id: str
    based_on_seq: int
    suggested_reply: str
    confidence: float


class ScoreEvent(BaseEvent):
    call_id: str
    score: int
    tags: list[str]


class RouteDecisionEvent(BaseEvent):
    call_id: str
    route: Route
    confidence: float
    based_on_seq: int
