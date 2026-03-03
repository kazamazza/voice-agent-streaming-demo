from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    AppConfig,
    RoutingConfig,
    TaxonomyConfig,
    MessagesConfig, ScoringConfig,
)


def load_config(path: str = "config/routing.yaml") -> AppConfig:
    """
    Load application config from YAML file and map into strongly-typed config objects.

    Fails fast if required sections are missing.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text())

    if not isinstance(raw, dict):
        raise ValueError("Invalid config format: root must be a mapping")

    # --- Routing ---
    routing_raw = raw.get("routing")
    if not routing_raw:
        raise ValueError("Missing 'routing' section in config")

    routing_cfg = RoutingConfig(
        min_chunks_for_clarify=int(routing_raw["min_chunks_for_clarify"]),
        min_chunks_for_llm_fallback=int(routing_raw["min_chunks_for_llm_fallback"]),
        rules=dict(routing_raw["rules"]),
        clarification_message=raw["messages"]["clarification"]["en"],
    )

    # --- Taxonomy ---
    taxonomy_raw = raw.get("taxonomy", {})

    taxonomy_cfg = TaxonomyConfig(
        greeting=list(taxonomy_raw.get("greeting", [])),
        empathy=list(taxonomy_raw.get("empathy", [])),
        billing_topic=list(taxonomy_raw.get("billing_topic", [])),
    )

    # --- Messages ---
    messages_raw = raw.get("messages", {})

    messages_cfg = MessagesConfig(
        clarification=messages_raw.get("clarification", {}).get("en", ""),
        baseline_suggestion=messages_raw.get("baseline_suggestion", {}).get("en", ""),
        empty_suggestion=messages_raw.get("empty_suggestion", {}).get("en", ""),
        coaching_default=messages_raw.get("coaching_default", {}).get("en", ""),
        invalid_suggestion_fallback=messages_raw.get("invalid_suggestion_fallback", {}).get("en", ""),
    )

    # --- Scoring ---
    scoring_raw = raw.get("scoring", {})
    scoring_cfg = ScoringConfig(
        greeting_bonus=int(scoring_raw.get("greeting_bonus", 5)),
        greeting_penalty=int(scoring_raw.get("greeting_penalty", 10)),
        empathy_bonus=int(scoring_raw.get("empathy_bonus", 5)),
        base_score=int(scoring_raw.get("base_score", 70)),
    )

    return AppConfig(
        routing=routing_cfg,
        taxonomy=taxonomy_cfg,
        messages=messages_cfg,
        scoring=scoring_cfg
    )