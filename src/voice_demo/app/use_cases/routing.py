from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.domain.models import RouteDecision
from voice_demo.ports.state_store import StateStorePort
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.llm import LLMProviderPort
from voice_demo.app.events import RouteDecisionEvent


@dataclass
class RoutingEngine:
    state: StateStorePort
    broker: BrokerPort
    llm: LLMProviderPort
    out_stream: str = "routes"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        session = self.state.get_session(call_id)
        if not session:
            return

        t = session.transcript_text().lower()

        # Layer 1: deterministic routing
        if any(x in t for x in ["refund", "charge", "invoice", "billing"]):
            route, conf, reason = "BILLING", 0.9, "billing keywords"
        elif any(x in t for x in ["bug", "error", "not working", "issue", "support"]):
            route, conf, reason = "SUPPORT", 0.85, "support keywords"
        elif any(x in t for x in ["pricing", "quote", "buy", "purchase", "sales"]):
            route, conf, reason = "SALES", 0.85, "sales keywords"
        else:
            # Not enough evidence yet: ask clarification (agent assist suggestion)
            # We keep route UNKNOWN until we have more context.
            route, conf, reason = "UNKNOWN", 0.3, "insufficient evidence"

        # Optional: LLM fallback only if still UNKNOWN after some context
        if route == "UNKNOWN" and session.last_seq >= 3:
            try:
                llm_route, llm_conf = self.llm.classify_intent(session.transcript_text())
                route, conf, reason = llm_route, float(llm_conf), "llm fallback"
            except Exception:
                pass

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

        evt = RouteDecisionEvent(
            call_id=call_id,
            route=route,  # type: ignore
            confidence=float(conf),
            based_on_seq=session.last_seq,
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump())