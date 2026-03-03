from __future__ import annotations

import json
from datetime import datetime

import redis
from typing import Optional

from voice_demo.ports.state_store import StateStorePort
from voice_demo.domain.models import CallSession, TranscriptChunk, Suggestion, Score, RouteDecision


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _dt_from_iso(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


def _chunk_to_dict(c: TranscriptChunk) -> dict:
    return {
        "call_id": c.call_id,
        "seq": c.seq,
        "ts": c.ts.isoformat(),
        "text": c.text,
        "event_id": c.event_id,
        "source": c.source,
        "schema_version": c.schema_version,
    }


def _chunk_from_dict(d: dict) -> TranscriptChunk:
    return TranscriptChunk(
        call_id=d["call_id"],
        seq=int(d["seq"]),
        ts=datetime.fromisoformat(d["ts"]),
        text=d["text"],
        event_id=d["event_id"],
        source=d.get("source", "stt"),
        schema_version=int(d.get("schema_version", 1)),
    )

class RedisStateStore(StateStorePort):
    def __init__(self, redis_client: redis.Redis):
        self._r = redis_client

    def _session_key(self, call_id: str) -> str:
        return f"session:{call_id}"

    def _events_key(self, call_id: str) -> str:
        return f"session:{call_id}:events"

    def get_session(self, call_id: str) -> Optional[CallSession]:
        raw = self._r.get(self._session_key(call_id))
        if not raw:
            return None

        d = json.loads(raw)
        session = CallSession(
            call_id=d["call_id"],
            last_seq=int(d.get("last_seq", -1)),
            rolling_summary=d.get("rolling_summary", ""),
            recent_chunks=[_chunk_from_dict(x) for x in d.get("recent_chunks", [])],
        )

        # Optional fields (we’ll keep them lenient)
        if d.get("latest_suggestion"):
            session.latest_suggestion = Suggestion(**d["latest_suggestion"])
        if d.get("latest_score"):
            session.latest_score = Score(**d["latest_score"])
        if d.get("latest_route"):
            session.latest_route = RouteDecision(**d["latest_route"])

        return session

    def save_session(self, session: CallSession) -> None:
        payload = {
            "call_id": session.call_id,
            "last_seq": session.last_seq,
            "rolling_summary": session.rolling_summary,
            "recent_chunks": [_chunk_to_dict(c) for c in session.recent_chunks],
            "latest_suggestion": (session.latest_suggestion.__dict__ if session.latest_suggestion else None),
            "latest_score": (session.latest_score.__dict__ if session.latest_score else None),
            "latest_route": (session.latest_route.__dict__ if session.latest_route else None),
        }
        self._r.set(self._session_key(session.call_id), json.dumps(payload))

    def has_processed_event(self, call_id: str, event_id: str) -> bool:
        return bool(self._r.sismember(self._events_key(call_id), event_id))

    def mark_event_processed(self, call_id: str, event_id: str) -> None:
        self._r.sadd(self._events_key(call_id), event_id)