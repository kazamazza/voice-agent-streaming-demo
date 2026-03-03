from dataclasses import dataclass


@dataclass(frozen=True)
class MessagesConfig:
    clarification: str
    baseline_suggestion: str
    empty_suggestion: str
    invalid_suggestion_fallback: str
    coaching_default: str


@dataclass(frozen=True)
class RoutingConfig:
    min_chunks_for_clarify: int
    min_chunks_for_llm_fallback: int
    rules: dict[str, list[str]]
    clarification_message: str


@dataclass(frozen=True)
class ScoringConfig:
    greeting_bonus: int = 5
    greeting_penalty: int = 10
    empathy_bonus: int = 5
    base_score: int = 70


@dataclass(frozen=True)
class SemanticConfig:
    enabled: bool
    threshold: float


@dataclass(frozen=True)
class TaxonomyConfig:
    greeting: list[str]
    empathy: list[str]
    billing_topic: list[str]
    intent_descriptions: dict[str, str]


@dataclass(frozen=True)
class AppConfig:
    routing: RoutingConfig
    taxonomy: TaxonomyConfig
    messages: MessagesConfig
    scoring: ScoringConfig
    semantic: SemanticConfig