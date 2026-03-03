from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.config.models import ScoringConfig
from voice_demo.domain.models import Score
from voice_demo.ports.state_store import StateStorePort
from voice_demo.ports.broker import BrokerPort
from voice_demo.app.events import ScoreEvent


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


@dataclass
class ScoringEngine:
    state: StateStorePort
    broker: BrokerPort
    cfg: ScoringConfig
    out_stream: str = "scores"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        t = session.transcript_text().lower()
        tags: list[str] = []
        score = 70

        # Greeting
        if _contains_any(t, self.cfg.taxonomy.greeting):
            tags.append("HAS_GREETING")
            score += 5
        else:
            tags.append("NO_GREETING")
            score -= 10

        # Empathy
        if _contains_any(t, self.cfg.taxonomy.empathy):
            tags.append("HAS_EMPATHY")
            score += 5

        # Topic tags (example)
        if _contains_any(t, self.cfg.taxonomy.billing_topic):
            tags.append("BILLING_TOPIC")

        score = max(0, min(100, score))
        coaching = self.cfg.messages.coaching_default

        s = Score(call_id=call_id, score=score, tags=tags, coaching_note=coaching)
        s.validate()

        session.latest_score = s
        self.state.save_session(session)

        evt = ScoreEvent(call_id=call_id, score=score, tags=tags, trace_id=trace_id)
        self.broker.publish(self.out_stream, evt.model_dump(mode="json"))