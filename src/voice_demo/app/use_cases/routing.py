from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.config.models import AppConfig
from voice_demo.domain.constants import Route
from voice_demo.domain.models import RouteDecision, Suggestion
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.semantic_intent import SemanticIntentPort
from voice_demo.ports.state_store import StateStorePort
from .routing_resolvers import KeywordRouteResolver, LLMRouteResolver, SemanticRouteResolver
from .routing_types import RouteCandidate
from ..events import RouteDecisionEvent
from ...ports.llm import LLMProviderPort


@dataclass
class RoutingEngine:
    state: StateStorePort
    broker: BrokerPort
    semantic: SemanticIntentPort
    llm: LLMProviderPort
    cfg: AppConfig
    out_stream: str = "routes"

    def _resolve_route(self, session) -> RouteCandidate:
        """
        Chain of Responsibility:
          1) keyword (fast)
          2) semantic (NLP-ish)
          3) LLM fallback (slow/$$)
        """
        resolvers = [
            KeywordRouteResolver(cfg=self.cfg),
            SemanticRouteResolver(cfg=self.cfg, semantic=self.semantic),
            LLMRouteResolver(cfg=self.cfg, llm=self.llm),
        ]

        for r in resolvers:
            cand = r.resolve(session)
            if cand is not None:
                return cand

        return RouteCandidate(route=Route.UNKNOWN, confidence=0.3, reason="insufficient_evidence")

    def _maybe_set_clarification(self, call_id: str, session) -> None:
        """
        If still UNKNOWN after N chunks, set clarification suggestion (agent-assist),
        but avoid overwriting existing clarification for the same seq.
        """
        if session.last_seq < int(self.cfg.routing.min_chunks_for_clarify):
            return

        if session.latest_suggestion:
            is_clarification = "clarification" in (session.latest_suggestion.rationale or "").lower()
            if is_clarification and session.latest_suggestion.based_on_seq >= session.last_seq:
                return

        msg = self.cfg.messages.clarification or self.cfg.routing.clarification_message
        if not msg:
            msg = "Just to clarify — is this about billing, technical support, or sales?"

        try:
            s = Suggestion(
                call_id=call_id,
                based_on_seq=session.last_seq,
                suggested_reply=msg,
                confidence=0.6,
                rationale="clarification: route unknown",
            )
            s.validate()
            session.latest_suggestion = s
        except Exception:
            # never crash routing on suggestion issues
            return

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        """
        Routing use-case (latency-first):

          1) Resolve route via CoR: keyword -> semantic -> LLM
          2) If still UNKNOWN and enough context -> set clarification suggestion
          3) Persist session once
          4) Publish RouteDecisionEvent
        """
        session = self.state.get_session(call_id)
        if not session:
            return

        cand = self._resolve_route(session)

        # Clarify if still unknown
        if cand.route == Route.UNKNOWN:
            self._maybe_set_clarification(call_id, session)

        decision = RouteDecision(
            call_id=call_id,
            route=cand.route,
            confidence=float(cand.confidence),
            reason=str(cand.reason),
            based_on_seq=session.last_seq,
        )
        decision.validate()

        session.latest_route = decision
        session.latest_trace_id = trace_id
        self.state.save_session(session)

        evt = RouteDecisionEvent(
            call_id=call_id,
            route=cand.route,
            confidence=float(cand.confidence),
            based_on_seq=session.last_seq,
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump(mode="json"))