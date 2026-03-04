from datetime import datetime, timezone

import pytest

from voice_demo.domain.models import TranscriptChunk
from voice_demo.domain.errors import InvalidChunk


def test_transcript_chunk_validates_ok():
    c = TranscriptChunk(call_id="call-1", seq=0, ts=datetime.now(timezone.utc), text="hello")
    c.validate()


def test_transcript_chunk_rejects_large_text():
    c = TranscriptChunk(call_id="call-1", seq=0, ts=datetime.now(timezone.utc), text="x" * 2001)
    with pytest.raises(InvalidChunk):
        c.validate()


def test_transcript_chunk_rejects_negative_seq():
    c = TranscriptChunk(call_id="call-1", seq=-1, ts=datetime.now(timezone.utc), text="hi")
    with pytest.raises(InvalidChunk):
        c.validate()
