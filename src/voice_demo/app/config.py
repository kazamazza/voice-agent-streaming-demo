from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import yaml


@dataclass(frozen=True)
class RoutingConfig:
    min_chunks_for_clarify: int
    min_chunks_for_llm_fallback: int
    rules: Dict[str, List[str]]
    clarification_message: str


def load_routing_config(path: str = "config/app.yaml") -> RoutingConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    routing = data["routing"]
    rules = routing["rules"]
    msg = data["messages"]["clarification"]["en"]

    return RoutingConfig(
        min_chunks_for_clarify=int(routing.get("min_chunks_for_clarify", 2)),
        min_chunks_for_llm_fallback=int(routing.get("min_chunks_for_llm_fallback", 3)),
        rules={k: list(v) for k, v in rules.items()},
        clarification_message=str(msg),
    )
