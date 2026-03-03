from __future__ import annotations
from dataclasses import dataclass
from voice_demo.domain.constants import Route

@dataclass(frozen=True)
class RouteCandidate:
    route: Route
    confidence: float
    reason: str