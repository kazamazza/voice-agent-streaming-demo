import redis

from voice_demo.adapters.llm_stub import StubLLMProvider
from voice_demo.adapters.semantic_model_intent import ModelSemanticIntent
from voice_demo.adapters.semantic_stub import StubSemanticIntent
from voice_demo.config.loader import load_config
from voice_demo.ports.semantic_intent import SemanticIntentPort
from voice_demo.settings import Settings
from voice_demo.adapters.broker_redis_streams import RedisStreamsBroker
from voice_demo.adapters.state_redis import RedisStateStore


def build_container() -> dict:
    settings = Settings()
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    broker = RedisStreamsBroker(redis_client)
    state_store = RedisStateStore(redis_client)

    app_cfg = load_config()
    llm = StubLLMProvider()

    # ---- Semantic intent provider (DI) ----
    provider = (app_cfg.semantic.provider or "stub").lower()

    if not app_cfg.semantic.enabled or provider == "stub":
        semantic: SemanticIntentPort = StubSemanticIntent()

    elif provider == "model":
        if not app_cfg.semantic.model_path:
            raise ValueError("semantic.model_path is required when semantic.provider='model'")
        semantic = ModelSemanticIntent(model_path=app_cfg.semantic.model_path)

    elif provider == "openai":
        # Future hook (keep demo keyless)
        semantic = StubSemanticIntent()

    else:
        raise ValueError(f"Invalid semantic.provider: {app_cfg.semantic.provider}")

    return {
        "settings": settings,
        "redis_client": redis_client,
        "broker": broker,
        "state_store": state_store,
        "config": app_cfg,
        "llm": llm,
        "semantic": semantic,
    }
