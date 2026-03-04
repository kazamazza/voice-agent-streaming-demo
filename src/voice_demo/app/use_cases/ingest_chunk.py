from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from voice_demo.domain.models import TranscriptChunk, CallSession
from voice_demo.domain.errors import OutOfOrderSeq, DuplicateEvent
from voice_demo.ports.broker import BrokerPort
from voice_demo.ports.state_store import StateStorePort
from voice_demo.app.events import TranscriptChunkEvent


@dataclass
class IngestChunk:
    broker: BrokerPort
    state: StateStorePort
    stream_name: str = "transcript_chunks"

    def handle(self, chunk: TranscriptChunk, *, trace_id: Optional[str] = None) -> None:
        chunk.validate()

        # idempotency: if already processed, raise (API can treat as 200/202)
        if self.state.has_processed_event(chunk.call_id, chunk.event_id):
            raise DuplicateEvent(event_id=chunk.event_id)

        session = self.state.get_session(chunk.call_id) or CallSession(call_id=chunk.call_id)

        expected_next = session.last_seq + 1
        if chunk.seq != expected_next:
            raise OutOfOrderSeq(expected_next=expected_next, got=chunk.seq)

        # update state now (so API writes are consistent)
        session.apply_chunk(chunk)
        self.state.save_session(session)
        self.state.mark_event_processed(chunk.call_id, chunk.event_id)

        # publish event for downstream workers
        evt = TranscriptChunkEvent(
            call_id=chunk.call_id,
            seq=chunk.seq,
            ts=chunk.ts,
            text=chunk.text,
            source=chunk.source,
            trace_id=trace_id,
            event_id=chunk.event_id,
        )
        self.broker.publish(self.stream_name, evt.model_dump(mode="json"))
