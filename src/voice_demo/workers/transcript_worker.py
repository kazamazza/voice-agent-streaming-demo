from __future__ import annotations

import time
import logging

from voice_demo.container import build_container
from voice_demo.app.use_cases.suggestion import SuggestionEngine
from voice_demo.app.use_cases.scoring import ScoringEngine
from voice_demo.app.use_cases.routing import RoutingEngine
from voice_demo.app.config import load_routing_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_transcript_worker():
    container = build_container()
    broker = container["broker"]
    state = container["state_store"]

    # Stub LLM provider for now
    class StubLLM:
        def classify_intent(self, transcript: str):
            return "UNKNOWN", 0.5

        def generate_suggestion(self, transcript: str):
            return "Let me check that for you.", 0.6

    llm = StubLLM()

    cfg = load_routing_config()

    suggestion_engine = SuggestionEngine(state=state, broker=broker, llm=llm)
    scoring_engine = ScoringEngine(state=state, broker=broker)
    routing_engine = RoutingEngine(state=state, broker=broker, llm=llm, cfg=cfg)

    stream = "transcript_chunks"
    group = "transcript_group"
    consumer = "worker-1"

    logger.info("Transcript worker started")

    while True:
        messages = broker.consume(stream, group, consumer, count=10, block_ms=2000)

        for msg in messages:
            call_id = msg["call_id"]
            message_id = msg["_message_id"]

            try:
                suggestion_engine.handle_call(call_id)
                scoring_engine.handle_call(call_id)
                routing_engine.handle_call(call_id)

                broker.ack(stream, group, message_id)
                logger.info(f"Processed chunk for call_id={call_id}")
            except Exception:
                logger.exception("Worker error — not acking message")

        time.sleep(0.1)


if __name__ == "__main__":
    run_transcript_worker()