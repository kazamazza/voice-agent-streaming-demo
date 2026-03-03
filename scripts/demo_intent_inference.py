from pathlib import Path
import joblib

MODEL = Path("models/intent_model.joblib")

examples = [
    "money was taken from my card two times",
    "the app keeps crashing when I try to login",
    "I want to buy your premium plan",
    "can you connect me to a human agent",
]

pipe = joblib.load(MODEL)

for text in examples:
    probs = pipe.predict_proba([text])[0]
    classes = getattr(pipe, "classes_", getattr(pipe[-1], "classes_", []))

    ranked = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)

    print("\nTEXT:", text)

    for label, score in ranked[:3]:
        print(f"  {label:<12} {score:.3f}")