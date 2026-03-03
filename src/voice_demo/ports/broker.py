from __future__ import annotations

from typing import Protocol, Iterable


class BrokerPort(Protocol):
    """
    Abstraction over event streaming infrastructure (Redis Streams, Kafka, etc).
    """

    def publish(self, stream: str, event: dict) -> None:
        ...

    def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 1000,
    ) -> Iterable[dict]:
        ...

    def ack(self, stream: str, group: str, message_id: str) -> None:
        ...