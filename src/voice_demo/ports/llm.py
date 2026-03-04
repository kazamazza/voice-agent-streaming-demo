from __future__ import annotations

from typing import Protocol


class LLMProviderPort(Protocol):
    """
    Abstraction over LLM classification/suggestion provider.
    """

    def classify_intent(self, transcript: str) -> tuple[str, float]:
        """
        Returns (route, confidence)
        """
        ...

    def generate_suggestion(self, transcript: str) -> tuple[str, float]:
        """
        Returns (suggested_reply, confidence)
        """
        ...
