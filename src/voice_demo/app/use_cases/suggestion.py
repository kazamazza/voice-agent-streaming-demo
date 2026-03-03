from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import time

from voice_demo.domain.models import Suggestion, CallSession
from voice_demo.ports.llm import LLMProviderPort
from voice_demo.ports.state_store import StateStorePort
from voice_demo.ports.broker import BrokerPort
from voice_demo.app.events import SuggestionEvent


@dataclass
class SuggestionEngine:
    state: StateStorePort
    broker: BrokerPort
    llm: LLMProviderPort
    out_stream: str = "suggestions"

    # simple circuit breaker
    fail_count: int = 0
    disabled_until: float = 0.0

    def _baseline(self, transcript: str) -> tuple[str, float]:
        if not transcript:
            return ("Could you tell me a bit more about what you need help with?", 0.4)
        return ("I understand — can you confirm your account email and the issue you're seeing?", 0.55)

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        transcript = session.transcript_text()

        # default: baseline
        reply, conf = self._baseline(transcript)

        now = time.time()
        if now >= self.disabled_until:
            try:
                llm_reply, llm_conf = self.llm.generate_suggestion(transcript)
                reply, conf = llm_reply, llm_conf
                self.fail_count = 0
            except Exception:
                self.fail_count += 1
                if self.fail_count >= 3:
                    self.disabled_until = now + 120  # 2 min cool-off

        suggestion = Suggestion(
            call_id=call_id,
            based_on_seq=session.last_seq,
            suggested_reply=reply,
            confidence=float(conf),
            rationale="baseline/llm hybrid",
        )
        suggestion.validate()
        session.latest_suggestion = suggestion
        self.state.save_session(session)

        evt = SuggestionEvent(
            call_id=call_id,
            based_on_seq=session.last_seq,
            suggested_reply=reply,
            confidence=float(conf),
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump())