from __future__ import annotations

import json

import redis
from typing import Optional

from voice_demo.adapters.serializers.session_serializer import deserialize_session, serialize_session
from voice_demo.ports.state_store import StateStorePort
from voice_demo.domain.models import CallSession



class RedisStateStore(StateStorePort):
    def __init__(self, redis_client: redis.Redis):
        self._r = redis_client

    def _session_key(self, call_id: str) -> str:
        return f"session:{call_id}"

    def _events_key(self, call_id: str) -> str:
        return f"session:{call_id}:events"

    def get_session(self, call_id: str) -> Optional[CallSession]:
        raw = self._r.get(self._session_key(call_id))
        if not raw:
            return None
        return deserialize_session(json.loads(raw))

    def save_session(self, session: CallSession) -> None:
        self._r.set(self._session_key(session.call_id), json.dumps(serialize_session(session)))

    def has_processed_event(self, call_id: str, event_id: str) -> bool:
        return bool(self._r.sismember(self._events_key(call_id), event_id))

    def mark_event_processed(self, call_id: str, event_id: str) -> None:
        self._r.sadd(self._events_key(call_id), event_id)