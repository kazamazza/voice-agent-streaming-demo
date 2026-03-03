from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from voice_demo.domain.models import CallSession, TranscriptChunk, Suggestion, Score, RouteDecision


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _dt_from_iso(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


def _chunk_to_dict(c: TranscriptChunk) -> dict[str, Any]:
    return {
        "call_id": c.call_id,
        "seq": c.seq,
        "ts": _dt_to_iso(c.ts),
        "text": c.text,
        "event_id": c.event_id,
        "source": c.source,
        "schema_version": c.schema_version,
    }


def _chunk_from_dict(d: dict[str, Any]) -> TranscriptChunk:
    return TranscriptChunk(
        call_id=d["call_id"],
        seq=int(d["seq"]),
        ts=_dt_from_iso(d["ts"]),  # type: ignore[arg-type]
        text=d["text"],
        event_id=d["event_id"],
        source=d.get("source", "stt"),
        schema_version=int(d.get("schema_version", 1)),
    )


def _suggestion_to_dict(s: Suggestion) -> dict[str, Any]:
    d = asdict(s)
    d["ts"] = _dt_to_iso(s.ts)
    return d


def _score_to_dict(s: Score) -> dict[str, Any]:
    d = asdict(s)
    d["ts"] = _dt_to_iso(s.ts)
    return d


def _route_to_dict(r: RouteDecision) -> dict[str, Any]:
    d = asdict(r)
    d["ts"] = _dt_to_iso(r.ts)
    return d


def _suggestion_from_dict(d: dict[str, Any]) -> Suggestion:
    d = dict(d)
    d["ts"] = _dt_from_iso(d.get("ts"))
    return Suggestion(**d)  # type: ignore[arg-type]


def _score_from_dict(d: dict[str, Any]) -> Score:
    d = dict(d)
    d["ts"] = _dt_from_iso(d.get("ts"))
    return Score(**d)  # type: ignore[arg-type]


def _route_from_dict(d: dict[str, Any]) -> RouteDecision:
    d = dict(d)
    d["ts"] = _dt_from_iso(d.get("ts"))
    return RouteDecision(**d)  # type: ignore[arg-type]


def serialize_session(session: CallSession) -> dict[str, Any]:
    return {
        "call_id": session.call_id,
        "last_seq": session.last_seq,
        "rolling_summary": session.rolling_summary,
        "recent_chunks": [_chunk_to_dict(c) for c in session.recent_chunks],
        "latest_suggestion": _suggestion_to_dict(session.latest_suggestion) if session.latest_suggestion else None,
        "latest_score": _score_to_dict(session.latest_score) if session.latest_score else None,
        "latest_route": _route_to_dict(session.latest_route) if session.latest_route else None,
        "latest_trace_id": session.latest_trace_id
    }


def deserialize_session(d: dict[str, Any]) -> CallSession:
    session = CallSession(
        call_id=d["call_id"],
        last_seq=int(d.get("last_seq", -1)),
        rolling_summary=d.get("rolling_summary", ""),
        recent_chunks=[_chunk_from_dict(x) for x in d.get("recent_chunks", [])],
    )
    session.latest_trace_id = d.get("latest_trace_id")

    ls = d.get("latest_suggestion")
    if ls:
        session.latest_suggestion = _suggestion_from_dict(ls)

    sc = d.get("latest_score")
    if sc:
        session.latest_score = _score_from_dict(sc)

    lr = d.get("latest_route")
    if lr:
        session.latest_route = _route_from_dict(lr)

    return session