from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Optional

from openai import OpenAI

from voice_demo.domain.constants import Route
from voice_demo.ports.semantic_intent import IntentScore, SemanticIntentPort


def _cosine(a: list[float], b: list[float]) -> float:
    # safe cosine similarity
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        na += x * x
        nb += y * y
    denom = sqrt(na) * sqrt(nb)
    if denom <= 0.0:
        return 0.0
    return dot / denom


@dataclass
class OpenAIEmbeddingsSemanticIntent(SemanticIntentPort):
    api_key: str
    intent_descriptions: dict[Route, str]
    model: str = "text-embedding-3-small"

    _client: Optional[OpenAI] = None
    _intent_vectors: Optional[dict[Route, list[float]]] = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def _embed(self, text: str) -> list[float]:
        client = self._get_client()
        r = client.embeddings.create(model=self.model, input=text)
        return list(r.data[0].embedding)

    def _ensure_intent_vectors(self) -> None:
        if self._intent_vectors is not None:
            return

        vectors: dict[Route, list[float]] = {}
        for intent, desc in self.intent_descriptions.items():
            if not desc:
                continue
            vectors[intent] = self._embed(desc)
        self._intent_vectors = vectors

    def rank_intents(self, transcript: str) -> list[IntentScore]:
        transcript = (transcript or "").strip()
        if not transcript:
            return [IntentScore(Route.UNKNOWN, 0.0)]

        self._ensure_intent_vectors()
        if not self._intent_vectors:
            return [IntentScore(Route.UNKNOWN, 0.0)]

        tvec = self._embed(transcript)

        scores: list[IntentScore] = []
        for intent, ivec in self._intent_vectors.items():
            score = _cosine(tvec, ivec)
            scores.append(IntentScore(intent=intent, score=float(score)))

        scores.sort(key=lambda x: x.score, reverse=True)
        return scores
