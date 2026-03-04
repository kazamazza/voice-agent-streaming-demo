from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from voice_demo.app.events import SuggestionEvent
from voice_demo.config.models import AppConfig
from voice_demo.domain.models import Suggestion
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.llm import LLMProviderPort
from voice_demo.ports.state_store import StateStorePort


@dataclass
class SuggestionEngine:
    state: StateStorePort
    broker: BrokerPort
    llm: LLMProviderPort
    cfg: AppConfig
    out_stream: str = "suggestions"

    # simple circuit breaker (process-local)
    fail_count: int = 0
    disabled_until: float = 0.0

    def _baseline(self, transcript: str) -> tuple[str, float]:
        if not transcript:
            return (self.cfg.messages.empty_suggestion, 0.4)
        return (self.cfg.messages.baseline_suggestion, 0.55)

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        # 1) If routing already set a clarification suggestion for the latest seq, preserve it.
        if (
            session.latest_suggestion
            and session.latest_suggestion.based_on_seq >= session.last_seq
            and "clarification" in (session.latest_suggestion.rationale or "").lower()
        ):
            return

        # 2) If we already generated a non-clarification suggestion for this seq, don't spam/overwrite.
        if session.latest_suggestion and session.latest_suggestion.based_on_seq >= session.last_seq:
            return

        transcript = session.transcript_text()

        # default: baseline
        reply, conf = self._baseline(transcript)
        rationale = "baseline"

        # optional: LLM assist (guarded by circuit breaker)
        now = time.time()
        if now >= self.disabled_until:
            try:
                llm_reply, llm_conf = self.llm.generate_suggestion(transcript)
                reply, conf = llm_reply, llm_conf
                rationale = "llm"
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
            rationale=rationale,
        )

        try:
            suggestion.validate()
        except Exception:
            # Safe fallback: always valid, always helpful
            reply = (
                "Sorry — could you clarify what you need help with (billing, support, or sales)?"
            )
            conf = 0.4
            suggestion = Suggestion(
                call_id=call_id,
                based_on_seq=session.last_seq,
                suggested_reply=reply,
                confidence=float(conf),
                rationale="fallback: invalid suggestion",
            )
            suggestion.validate()

        session.latest_suggestion = suggestion
        session.latest_trace_id = trace_id
        self.state.save_session(session)

        evt = SuggestionEvent(
            call_id=call_id,
            based_on_seq=session.last_seq,
            suggested_reply=suggestion.suggested_reply,
            confidence=float(suggestion.confidence),
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump(mode="json"))
