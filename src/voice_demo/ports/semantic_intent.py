from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from voice_demo.domain.constants import Route


@dataclass(frozen=True)
class IntentScore:
    intent: Route
    score: float


class SemanticIntentPort(Protocol):
    def rank_intents(self, transcript: str) -> list[IntentScore]:
        ...