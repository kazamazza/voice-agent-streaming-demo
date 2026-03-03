from __future__ import annotations

from typing import Tuple

from voice_demo.ports.llm import LLMProviderPort


class StubLLMProvider(LLMProviderPort):
    def classify_intent(self, transcript: str) -> Tuple[str, float]:
        return "UNKNOWN", 0.5

    def generate_suggestion(self, transcript: str) -> Tuple[str, float]:
        return "Let me check that for you.", 0.6