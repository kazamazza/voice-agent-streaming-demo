from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    AppConfig,
    RoutingConfig,
    TaxonomyConfig,
    MessagesConfig, ScoringConfig, SemanticConfig,
)


def load_config(path: str = "config/app.yaml") -> AppConfig:
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

    # --- Semantic ---
    semantic_raw = raw.get("semantic", {}) or {}

    provider = str(semantic_raw.get("provider", "stub")).strip().lower()
    semantic_cfg = SemanticConfig(
        enabled=bool(semantic_raw.get("enabled", False)),
        threshold=float(semantic_raw.get("threshold", 0.78)),
        provider=provider,
        model_path=semantic_raw.get("model_path"),
    )

    if semantic_cfg.provider not in ("stub", "model", "openai"):
        raise ValueError(f"Invalid semantic.provider: {semantic_cfg.provider}")

    # Fail fast for model wiring
    if semantic_cfg.enabled and semantic_cfg.provider == "model" and not semantic_cfg.model_path:
        raise ValueError("semantic.model_path is required when semantic.enabled=true and provider='model'")


    # --- Taxonomy ---
    taxonomy_raw = raw.get("taxonomy", {})
    intent_desc = taxonomy_raw.get("intent_descriptions", {}) or {}
    taxonomy_cfg = TaxonomyConfig(
        greeting=list(taxonomy_raw.get("greeting", [])),
        empathy=list(taxonomy_raw.get("empathy", [])),
        billing_topic=list(taxonomy_raw.get("billing_topic", [])),
        intent_descriptions=dict(intent_desc),
    )

    return AppConfig(
        routing=routing_cfg,
        taxonomy=taxonomy_cfg,
        messages=messages_cfg,
        scoring=scoring_cfg,
        semantic=semantic_cfg,
    )