from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.app.config import RoutingConfig
from voice_demo.domain.models import RouteDecision, Suggestion
from voice_demo.ports.state_store import StateStorePort
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.llm import LLMProviderPort
from voice_demo.app.events import RouteDecisionEvent


@dataclass
class RoutingEngine:
    state: StateStorePort
    broker: BrokerPort
    llm: LLMProviderPort
    cfg: RoutingConfig
    out_stream: str = "routes"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        """
        Routing use-case (fast path first):
          1) Deterministic keyword routing (config-driven)
          2) If still UNKNOWN after N chunks -> set clarification suggestion (config-driven)
          3) Optional LLM fallback after M chunks
          4) Persist session once
          5) Publish RouteDecisionEvent
        """
        session = self.state.get_session(call_id)
        if not session:
            return

        transcript = session.transcript_text().lower()

        # ---- Layer 1: deterministic routing (fast + cheap) ----
        route, conf, reason = "UNKNOWN", 0.3, "insufficient evidence"
        for candidate_route, keywords in self.cfg.rules.items():
            if any(k in transcript for k in keywords):
                route = candidate_route
                conf = 0.9 if candidate_route == "BILLING" else 0.85
                reason = f"{candidate_route.lower()} keywords"
                break

        # ---- Clarification prompt (agent assist) if still UNKNOWN after some context ----
        if route == "UNKNOWN" and session.last_seq >= self.cfg.min_chunks_for_clarify:
            try:
                session.latest_suggestion = Suggestion(
                    call_id=call_id,
                    based_on_seq=session.last_seq,
                    suggested_reply=self.cfg.clarification_message,
                    confidence=0.6,
                    rationale="clarification: route unknown",
                )
                session.latest_suggestion.validate()
            except Exception:
                # Never crash routing because of a suggestion formatting issue
                session.latest_suggestion = Suggestion(
                    call_id=call_id,
                    based_on_seq=session.last_seq,
                    suggested_reply="Could you clarify whether this is about billing, support, or sales?",
                    confidence=0.5,
                    rationale="fallback clarification",
                )

        # ---- Optional: LLM fallback only if still UNKNOWN after more context ----
        if route == "UNKNOWN" and session.last_seq >= self.cfg.min_chunks_for_llm_fallback:
            try:
                llm_route, llm_conf = self.llm.classify_intent(session.transcript_text())
                # We only accept known routes; otherwise keep UNKNOWN.
                if llm_route in ("UNKNOWN", "SUPPORT", "SALES", "BILLING", "HUMAN_AGENT"):
                    route = llm_route
                    conf = float(llm_conf)
                    reason = "llm fallback"
            except Exception:
                pass

        # ---- Persist decision ----
        decision = RouteDecision(
            call_id=call_id,
            route=route,  # type: ignore
            confidence=float(conf),
            reason=reason,
            based_on_seq=session.last_seq,
        )
        decision.validate()

        session.latest_route = decision
        self.state.save_session(session)

        # ---- Emit event for downstream consumers ----
        evt = RouteDecisionEvent(
            call_id=call_id,
            route=route,  # type: ignore
            confidence=float(conf),
            based_on_seq=session.last_seq,
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump())