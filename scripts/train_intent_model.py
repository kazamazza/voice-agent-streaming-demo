from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from voice_demo.domain.time_utils import utcnow_iso

DATA = Path("data/processed/calls.parquet")
OUT = Path("models/intent_model.joblib")


def main() -> None:
    if not DATA.exists():
        raise FileNotFoundError(f"Missing dataset: {DATA}. Run: make parquet")

    df = pd.read_parquet(DATA)
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError("Dataset must contain columns: text, label")

    X = df["text"].fillna("").astype(str).tolist()
    y = df["label"].fillna("UNKNOWN").astype(str).tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y if len(set(y)) > 1 else None,
    )

    pipe: Pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000)),
            ("clf", LogisticRegression(max_iter=2000)),
        ]
    )

    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"accuracy={acc:.4f}")
    print(classification_report(y_test, preds, digits=3))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, OUT)
    print(f"Wrote model -> {OUT.resolve()}")

    # ---- sidecar metadata ----
    meta = {
        "model_name": "intent_model",
        "version": "1.0.0",
        "trained_at": utcnow_iso(),
        "dataset": str(DATA),
        "algorithm": "tfidf(1-2gram) + logistic_regression",
        "accuracy": float(acc),
        "labels": sorted({str(lbl).upper() for lbl in set(y)}),
    }

    meta_path = OUT.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"Wrote metadata -> {meta_path.resolve()}")


if __name__ == "__main__":
    main()
