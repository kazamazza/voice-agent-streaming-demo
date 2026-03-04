from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RouteLabel = Literal["BILLING", "SUPPORT", "SALES", "HUMAN_AGENT"]

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TRANSCRIPTS_PATH = RAW_DIR / "transcripts.jsonl"
LABELS_PATH = RAW_DIR / "labels.csv"


@dataclass(frozen=True)
class Template:
    label: RouteLabel
    openers: list[str]
    bodies: list[str]
    closers: list[str]


TEMPLATES: list[Template] = [
    Template(
        label="BILLING",
        openers=["Hi", "Hello", "Hey there"],
        bodies=[
            "you charged my card twice",
            "I was billed twice on my invoice",
            "my payment didn't go through but I see a pending charge",
            "I need a refund for a duplicate charge",
            "my subscription payment looks wrong",
        ],
        closers=["can you help?", "please fix this", "what can we do?"],
    ),
    Template(
        label="SUPPORT",
        openers=["Hi", "Hello", "Hey"],
        bodies=[
            "the app is not working",
            "I'm getting an error when I log in",
            "this feature is broken after the update",
            "I can't reset my password, it fails",
            "the website keeps crashing for me",
        ],
        closers=["can you troubleshoot?", "what should I do?", "can you assist?"],
    ),
    Template(
        label="SALES",
        openers=["Hi", "Hello"],
        bodies=[
            "can I get pricing for your enterprise plan?",
            "I'd like a quote for 50 seats",
            "can we upgrade our plan?",
            "do you offer discounts for annual billing?",
            "I want to buy this for my team",
        ],
        closers=["who can I talk to?", "can you send details?", "what are the options?"],
    ),
    Template(
        label="HUMAN_AGENT",
        openers=["Listen", "Hi", "Hello"],
        bodies=[
            "I want to speak to a human",
            "can you connect me to an agent?",
            "I need to escalate this to a manager",
            "this is unacceptable, I want someone real",
            "stop sending me automated replies",
        ],
        closers=["now please", "immediately", "this is urgent"],
    ),
]

FILLERS = [
    "thanks",
    "okay",
    "right",
    "I understand",
    "that's frustrating",
    "sorry",
]


def _rand_turns(t: Template) -> list[str]:
    # 2–5 turns
    n = random.randint(2, 5)
    turns: list[str] = []
    turns.append(f"{random.choice(t.openers)}")
    turns.append(f"{random.choice(t.bodies)}")
    while len(turns) < n - 1:
        turns.append(random.choice(FILLERS))
    turns.append(random.choice(t.closers))
    return turns


def main() -> None:
    random.seed(42)

    n_calls = int(
        (Path(ROOT / ".env").read_text().count("") and 0) or 500
    )  # harmless; overridden below
    # Prefer env var if you want; keep simple default otherwise:
    n_calls = int(__import__("os").getenv("SYNTH_CALLS", "800"))

    # Write labels.csv header
    LABELS_PATH.write_text("call_id,label\n", encoding="utf-8")

    with (
        TRANSCRIPTS_PATH.open("w", encoding="utf-8") as f_jsonl,
        LABELS_PATH.open("a", encoding="utf-8") as f_lbl,
    ):
        for _ in range(n_calls):
            call_id = f"call-{uuid.uuid4().hex[:10]}"
            t = random.choice(TEMPLATES)
            turns = _rand_turns(t)

            record = {
                "call_id": call_id,
                "label": t.label,
                "turns": [{"seq": i, "text": turns[i]} for i in range(len(turns))],
            }
            f_jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")
            f_lbl.write(f"{call_id},{t.label}\n")

    print(f"Wrote {n_calls} calls -> {TRANSCRIPTS_PATH}")
    print(f"Wrote labels -> {LABELS_PATH}")


if __name__ == "__main__":
    main()
