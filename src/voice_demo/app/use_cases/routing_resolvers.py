from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from voice_demo.config.models import AppConfig
from voice_demo.domain.constants import Route, ROUTE_VALUES
from voice_demo.domain.models import CallSession
from voice_demo.ports.semantic_intent import SemanticIntentPort

from .routing_types import RouteCandidate
from ...ports.llm import LLMProviderPort


class RouteResolver(Protocol):
    def resolve(self, session: CallSession) -> Optional[RouteCandidate]:
        ...


@dataclass
class KeywordRouteResolver(RouteResolver):
    cfg: AppConfig

    def resolve(self, session: CallSession) -> Optional[RouteCandidate]:
        transcript_lc = session.transcript_text().lower().strip()
        if not transcript_lc:
            return None

        for candidate_route_str, keywords in self.cfg.routing.rules.items():
            if candidate_route_str not in ROUTE_VALUES:
                continue
            if any(k in transcript_lc for k in keywords):
                route = Route(candidate_route_str)
                conf = 0.9 if route == Route.BILLING else 0.85
                reason = f"keyword_match:{route.value.lower()}"
                return RouteCandidate(route=route, confidence=float(conf), reason=reason)

        return None


@dataclass
class SemanticRouteResolver(RouteResolver):
    cfg: AppConfig
    semantic: SemanticIntentPort

    def resolve(self, session: CallSession) -> Optional[RouteCandidate]:
        if not self.cfg.semantic.enabled:
            return None

        transcript = session.transcript_text()
        if not transcript.strip():
            return None

        try:
            ranked = self.semantic.rank_intents(transcript)
        except Exception:
            return None

        if not ranked:
            return None

        best = max(ranked, key=lambda x: x.score)
        if best.intent == Route.UNKNOWN:
            return None
        if float(best.score) < float(self.cfg.semantic.threshold):
            return None

        return RouteCandidate(route=best.intent, confidence=float(best.score), reason="semantic_intent")


@dataclass
class LLMRouteResolver(RouteResolver):
    cfg: AppConfig
    llm: LLMProviderPort

    def resolve(self, session: CallSession) -> Optional[RouteCandidate]:
        if session.last_seq < int(self.cfg.routing.min_chunks_for_llm_fallback):
            return None

        transcript = session.transcript_text()
        if not transcript.strip():
            return None

        try:
            llm_route, llm_conf = self.llm.classify_intent(transcript)
            llm_route_str = str(llm_route).upper().strip()
        except Exception:
            return None

        if llm_route_str not in ROUTE_VALUES:
            return None

        return RouteCandidate(route=Route(llm_route_str), confidence=float(llm_conf), reason="llm_fallback")