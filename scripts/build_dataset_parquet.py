from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRANSCRIPTS_PATH = RAW_DIR / "transcripts.jsonl"
OUT_PARQUET = OUT_DIR / "calls.parquet"


def main() -> None:
    if not TRANSCRIPTS_PATH.exists():
        raise FileNotFoundError(f"Missing {TRANSCRIPTS_PATH}. Run: make data")

    rows: list[dict] = []

    with TRANSCRIPTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            call_id = d["call_id"]
            label = d["label"]
            turns = d.get("turns", [])
            text = " ".join((t.get("text") or "").strip() for t in turns).strip()
            rows.append(
                {
                    "call_id": call_id,
                    "label": label,
                    "text": text,
                    "turn_count": len(turns),
                }
            )

    df = pd.DataFrame(rows, columns=["call_id", "label", "text", "turn_count"])
    df.to_parquet(OUT_PARQUET, index=False)  # uses pyarrow if installed
    print(f"Wrote {len(df)} rows -> {OUT_PARQUET}")
    print(df.head(3).to_string(index=False))


if __name__ == "__main__":
    main()