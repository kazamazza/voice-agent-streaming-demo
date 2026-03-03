import redis

from voice_demo.adapters.llm_stub import StubLLMProvider
from voice_demo.config.loader import load_config
from voice_demo.settings import Settings
from voice_demo.adapters.broker_redis_streams import RedisStreamsBroker
from voice_demo.adapters.state_redis import RedisStateStore


def build_container():
    settings = Settings()
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    broker = RedisStreamsBroker(redis_client)
    state_store = RedisStateStore(redis_client)

    app_cfg = load_config()

    llm = StubLLMProvider()

    return {
        "settings": settings,
        "redis_client": redis_client,
        "broker": broker,
        "state_store": state_store,
        "config": app_cfg,
        "llm": llm,
    }