from __future__ import annotations

from dataclasses import dataclass

from voice_demo.domain.constants import Route
from voice_demo.ports.semantic_intent import IntentScore, SemanticIntentPort


@dataclass
class StubSemanticIntent(SemanticIntentPort):
    def rank_intents(self, transcript: str) -> list[IntentScore]:
        return [IntentScore(Route.UNKNOWN, 0.0)]