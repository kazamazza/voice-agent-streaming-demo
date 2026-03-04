from __future__ import annotations

import json
from typing import Iterable
import redis

from voice_demo.ports.broker import BrokerPort


class RedisStreamsBroker(BrokerPort):
    def __init__(self, redis_client: redis.Redis):
        self._r = redis_client

    def publish(self, stream: str, event: dict) -> None:
        # Redis Streams requires flat field/value pairs
        self._r.xadd(stream, {"data": json.dumps(event)})

    def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 1000,
    ) -> Iterable[dict]:
        try:
            messages = self._r.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
        except redis.ResponseError:
            # Group might not exist yet
            self._r.xgroup_create(stream, group, id="0", mkstream=True)
            return []

        results = []

        for _, entries in messages:
            for message_id, fields in entries:
                event_data = json.loads(fields["data"])
                event_data["_message_id"] = message_id
                results.append(event_data)

        return results

    def ack(self, stream: str, group: str, message_id: str) -> None:
        self._r.xack(stream, group, message_id)
