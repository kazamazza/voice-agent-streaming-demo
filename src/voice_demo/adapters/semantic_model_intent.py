from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib

from voice_demo.domain.constants import Route, ROUTE_VALUES
from voice_demo.ports.semantic_intent import IntentScore, SemanticIntentPort


logger = logging.getLogger(__name__)


@dataclass
class ModelSemanticIntent(SemanticIntentPort):
    model_path: str

    def __post_init__(self) -> None:
        p = Path(self.model_path)
        if not p.exists():
            raise FileNotFoundError(f"Semantic model not found: {p}")

        self._pipe = joblib.load(p)

        # We expect an sklearn Pipeline-like object with predict_proba.
        if not hasattr(self._pipe, "predict_proba"):
            raise TypeError("Loaded model must support predict_proba()")

        # Optional sidecar metadata
        meta_path = p.with_suffix(".meta.json")
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                logger.info(
                    "Loaded semantic model name=%s version=%s trained_at=%s accuracy=%s",
                    meta.get("model_name"),
                    meta.get("version"),
                    meta.get("trained_at"),
                    meta.get("accuracy"),
                )
            except Exception:
                logger.warning("Model metadata exists but failed to parse: %s", meta_path)

    def rank_intents(self, transcript: str) -> list[IntentScore]:
        text = (transcript or "").strip()
        if not text:
            return [IntentScore(intent=Route.UNKNOWN, score=0.0)]

        probs = self._pipe.predict_proba([text])[0]

        # classes_ may be on the pipeline or on the final estimator
        classes: Sequence[Any] | None = getattr(self._pipe, "classes_", None)
        if classes is None:
            try:
                classes = getattr(self._pipe[-1], "classes_", [])  # sklearn Pipeline supports [-1]
            except Exception:
                classes = []

        out: list[IntentScore] = []
        for label, prob in zip(classes, probs):
            name = str(label).upper().strip()
            if name in ROUTE_VALUES:
                out.append(IntentScore(intent=Route(name), score=float(prob)))
            else:
                out.append(IntentScore(intent=Route.UNKNOWN, score=float(prob)))

        out.sort(key=lambda x: x.score, reverse=True)
        return out
