import os
import redis

from voice_demo.adapters.broker_redis_streams import RedisStreamsBroker

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def test_publish_and_consume():
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    broker = RedisStreamsBroker(r)

    stream = "test_stream"
    group = "test_group"
    consumer = "c1"

    broker.publish(stream, {"hello": "world"})

    messages = broker.consume(stream, group, consumer)
    assert isinstance(messages, list)