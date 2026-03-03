from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.app.config import RoutingConfig
from voice_demo.app.events import RouteDecisionEvent
from voice_demo.domain.constants import ROUTE_VALUES, Route
from voice_demo.domain.models import RouteDecision, Suggestion
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.llm import LLMProviderPort
from voice_demo.ports.state_store import StateStorePort


@dataclass
class RoutingEngine:
    state: StateStorePort
    broker: BrokerPort
    llm: LLMProviderPort
    cfg: RoutingConfig
    out_stream: str = "routes"

    def handle_call(self, call_id: str, *, trace_id: Optional[str] = None) -> None:
        """
        Routing use-case (latency-first, deterministic-first):

          1) Deterministic keyword routing (config-driven)
          2) Optional LLM fallback after M chunks (ambiguity resolver)
          3) If still UNKNOWN after N chunks -> set clarification suggestion (agent-assist)
          4) Persist session once
          5) Publish RouteDecisionEvent

        Design goals:
          - Never crash the worker (routing is best-effort)
          - Prefer cheap decisions first
          - Avoid repeated clarification spam
          - Keep route enum internally; serialize as string in events
        """
        session = self.state.get_session(call_id)
        if not session:
            return

        transcript = session.transcript_text()
        transcript_lc = transcript.lower().strip()

        # ---- 1) Deterministic routing (fast + cheap) ----
        route: Route = Route.UNKNOWN
        conf: float = 0.3
        reason: str = "insufficient_evidence"

        for candidate_route_str, keywords in self.cfg.rules.items():
            if candidate_route_str not in ROUTE_VALUES:
                continue
            if any(k in transcript_lc for k in keywords):
                route = Route(candidate_route_str)
                conf = 0.9 if route == Route.BILLING else 0.85
                reason = f"keyword_match:{route.value.lower()}"
                break

        # ---- 2) Optional LLM fallback (only if still UNKNOWN and enough context) ----
        if route == Route.UNKNOWN and session.last_seq >= self.cfg.min_chunks_for_llm_fallback:
            try:
                llm_route, llm_conf = self.llm.classify_intent(transcript)
                llm_route_str = str(llm_route).upper().strip()
                if llm_route_str in ROUTE_VALUES:
                    route = Route(llm_route_str)
                    conf = float(llm_conf)
                    reason = "llm_fallback"
            except Exception:
                # LLM failures should never break routing
                pass

        # ---- 3) Clarification suggestion (only if STILL UNKNOWN and avoid spam) ----
        if route == Route.UNKNOWN and session.last_seq >= self.cfg.min_chunks_for_clarify:
            should_set = True

            # Avoid re-setting the same clarification on every new chunk
            if session.latest_suggestion:
                already_clarified = (
                    "clarification" in (session.latest_suggestion.rationale or "").lower()
                    and session.latest_suggestion.based_on_seq >= session.last_seq
                )
                if already_clarified:
                    should_set = False

            if should_set:
                # Prefer config message; fallback to same config if missing
                msg = self.cfg.clarification_message or (
                    "Just to clarify so I route you correctly — is this about billing, technical support, or sales?"
                )
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
                    # Never let a suggestion formatting issue crash routing
                    pass

        # ---- 4) Persist route decision ----
        decision = RouteDecision(
            call_id=call_id,
            route=route,
            confidence=float(conf),
            reason=reason,
            based_on_seq=session.last_seq,
        )
        decision.validate()

        session.latest_route = decision
        session.latest_trace_id = trace_id
        self.state.save_session(session)

        # ---- 5) Emit event ----
        evt = RouteDecisionEvent(
            call_id=call_id,
            route=route,  # keep enum in model; json mode will serialize to string
            confidence=float(conf),
            based_on_seq=session.last_seq,
            trace_id=trace_id,
        )
        self.broker.publish(self.out_stream, evt.model_dump(mode="json"))