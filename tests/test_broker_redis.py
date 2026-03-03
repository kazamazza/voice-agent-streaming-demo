import redis
from voice_demo.adapters.broker_redis_streams import RedisStreamsBroker


def test_publish_and_consume():
    r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    broker = RedisStreamsBroker(r)

    stream = "test_stream"
    group = "test_group"
    consumer = "c1"

    broker.publish(stream, {"hello": "world"})

    messages = broker.consume(stream, group, consumer)
    assert isinstance(messages, list)