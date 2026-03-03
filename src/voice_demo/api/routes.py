from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from voice_demo.domain.models import TranscriptChunk
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.state_store import StateStorePort
from voice_demo.app.use_cases.ingest_chunk import IngestChunk
from .deps import get_broker, get_state_store

import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

class IngestChunkBody(BaseModel):
    seq: int
    text: str
    ts: Optional[datetime] = None
    event_id: Optional[str] = None
    source: str = "stt"



@router.post("/calls/{call_id}/chunks", status_code=202)
def post_chunk(
    call_id: str,
    body: IngestChunkBody,
    broker: BrokerPort = Depends(get_broker),
    state: StateStorePort = Depends(get_state_store),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> dict:
    # ---- Trace ID generation ----
    trace_id = x_request_id or str(uuid.uuid4())

    ts = body.ts or datetime.now(timezone.utc)

    chunk = TranscriptChunk(
        call_id=call_id,
        seq=body.seq,
        ts=ts,
        text=body.text,
        source=body.source,
    )

    if body.event_id:
        object.__setattr__(chunk, "event_id", body.event_id)

    # ---- Structured log (API layer) ----
    logger.info(
        f"[trace={trace_id}] received_chunk call={call_id} seq={body.seq}"
    )

    # ---- Use case execution ----
    uc = IngestChunk(broker=broker, state=state)
    uc.handle(chunk, trace_id=trace_id)

    return {
        "ok": True,
        "call_id": call_id,
        "seq": body.seq,
        "request_id": trace_id,
    }


@router.get("/calls/{call_id}/agent_view")
def get_agent_view(
    call_id: str,
    state: StateStorePort = Depends(get_state_store),
) -> dict:
    session = state.get_session(call_id)

    if not session:
        return {
            "call_id": call_id,
            "trace_id": None,
            "last_seq": -1,
            "transcript": "",
            "suggestion": None,
            "score": None,
            "route": None,
        }

    return {
        "call_id": call_id,
        "trace_id": session.latest_trace_id,
        "last_seq": session.last_seq,
        "transcript": session.transcript_text(),
        "suggestion": (
            session.latest_suggestion.__dict__
            if session.latest_suggestion
            else None
        ),
        "score": (
            session.latest_score.__dict__
            if session.latest_score
            else None
        ),
        "route": (
            session.latest_route.__dict__
            if session.latest_route
            else None
        ),
    }