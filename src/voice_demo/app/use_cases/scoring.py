from dataclasses import dataclass
from typing import Optional
from voice_demo.app.events import ScoreEvent
from voice_demo.config.models import AppConfig
from voice_demo.domain.models import Score
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.state_store import StateStorePort


def _contains_any(text: str, phrases: list[str]) -> bool:
    if not text or not phrases:
        return False

    text = text.lower()
    return any(p.lower() in text for p in phrases if p)

@dataclass
class ScoringEngine:
    state: StateStorePort
    broker: BrokerPort
    cfg: AppConfig
    out_stream: str = "scores"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        transcript = session.transcript_text().lower()
        tags: list[str] = []

        # --- Base score from config ---
        score = self.cfg.scoring.base_score

        # --- Greeting detection ---
        if _contains_any(transcript, self.cfg.taxonomy.greeting):
            tags.append("HAS_GREETING")
            score += self.cfg.scoring.greeting_bonus
        else:
            tags.append("NO_GREETING")
            score -= self.cfg.scoring.greeting_penalty

        # --- Empathy detection ---
        if _contains_any(transcript, self.cfg.taxonomy.empathy):
            tags.append("HAS_EMPATHY")
            score += self.cfg.scoring.empathy_bonus

        # --- Topic tagging (no score impact here) ---
        if _contains_any(transcript, self.cfg.taxonomy.billing_topic):
            tags.append("BILLING_TOPIC")

        # --- Clamp score ---
        score = max(0, min(100, score))

        # --- Coaching message from config ---
        coaching = self.cfg.messages.coaching_default

        s = Score(
            call_id=call_id,
            score=score,
            tags=tags,
            coaching_note=coaching,
        )
        s.validate()

        # --- Persist session ---
        session.latest_score = s
        session.latest_trace_id = trace_id
        self.state.save_session(session)

        # --- Emit event ---
        evt = ScoreEvent(
            call_id=call_id,
            score=score,
            tags=tags,
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump(mode="json"))