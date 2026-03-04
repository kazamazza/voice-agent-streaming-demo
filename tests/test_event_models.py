from datetime import datetime, timezone
from voice_demo.app.events import TranscriptChunkEvent


def test_transcript_chunk_event_valid():
    e = TranscriptChunkEvent(call_id="call-1", seq=0, ts=datetime.now(timezone.utc), text="hello")
    assert e.call_id == "call-1"
