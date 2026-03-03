from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib

from voice_demo.domain.constants import Route
from voice_demo.ports.semantic_intent import IntentScore, SemanticIntentPort


@dataclass
class ModelSemanticIntent(SemanticIntentPort):
    model_path: str

    def __post_init__(self) -> None:
        p = Path(self.model_path)
        if not p.exists():
            raise FileNotFoundError(f"Semantic model not found: {p}")
        self._pipe = joblib.load(p)

        # We expect a sklearn Pipeline with predict_proba + classes_
        if not hasattr(self._pipe, "predict_proba"):
            raise TypeError("Loaded model must support predict_proba()")
        if not hasattr(self._pipe, "classes_"):
            # Pipeline exposes classes_ on final estimator in many cases; be lenient:
            pass

    def rank_intents(self, transcript: str) -> list[IntentScore]:
        text = (transcript or "").strip()
        if not text:
            return [IntentScore(intent=Route.UNKNOWN, score=0.0)]

        probs = self._pipe.predict_proba([text])[0]  # type: ignore[no-any-return]
        classes: Sequence[Any] = getattr(self._pipe, "classes_", None)

        # If classes_ not on pipeline, try final estimator
        if classes is None:
            classes = getattr(self._pipe[-1], "classes_", [])  # type: ignore[index]

        out: list[IntentScore] = []
        for label, p in zip(classes, probs):
            s = float(p)
            name = str(label).upper()
            intent = Route.UNKNOWN
            if name in (r.value for r in Route):
                intent = Route(name)
            out.append(IntentScore(intent=intent, score=s))

        out.sort(key=lambda x: x.score, reverse=True)
        return out