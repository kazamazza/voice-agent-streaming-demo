from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.domain.models import Score
from voice_demo.ports.state_store import StateStorePort
from voice_demo.ports.broker import BrokerPort
from voice_demo.app.events import ScoreEvent


@dataclass
class ScoringEngine:
    state: StateStorePort
    broker: BrokerPort
    out_stream: str = "scores"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        t = session.transcript_text().lower()
        tags: list[str] = []
        score = 70

        if any(x in t for x in ["hello", "hi", "good morning", "good afternoon"]):
            tags.append("HAS_GREETING")
            score += 5
        else:
            tags.append("NO_GREETING")
            score -= 10

        if any(x in t for x in ["sorry", "understand", "apologize", "i can help"]):
            tags.append("HAS_EMPATHY")
            score += 5

        if "refund" in t or "charged" in t or "invoice" in t:
            tags.append("BILLING_TOPIC")

        score = max(0, min(100, score))
        coaching = "Consider greeting the customer and confirming the issue clearly."

        s = Score(call_id=call_id, score=score, tags=tags, coaching_note=coaching)
        s.validate()
        session.latest_score = s
        self.state.save_session(session)

        evt = ScoreEvent(call_id=call_id, score=score, tags=tags, trace_id=trace_id)
        self.broker.publish(self.out_stream, evt.model_dump())