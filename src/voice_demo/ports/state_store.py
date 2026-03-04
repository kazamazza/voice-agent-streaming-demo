from __future__ import annotations

from typing import Protocol, Optional
from voice_demo.domain.models import CallSession


class StateStorePort(Protocol):
    """
    Abstraction over session state persistence (Redis, DB, etc).
    """

    def get_session(self, call_id: str) -> Optional[CallSession]: ...

    def save_session(self, session: CallSession) -> None: ...

    def has_processed_event(self, call_id: str, event_id: str) -> bool: ...

    def mark_event_processed(self, call_id: str, event_id: str) -> None: ...
