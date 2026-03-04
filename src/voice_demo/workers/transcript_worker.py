from __future__ import annotations

import json
import time
import logging

from voice_demo.container import build_container
from voice_demo.app.use_cases.suggestion import SuggestionEngine
from voice_demo.app.use_cases.scoring import ScoringEngine
from voice_demo.app.use_cases.routing import RoutingEngine


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_transcript_worker() -> None:
    """
    Worker entrypoint:
      - Consumes transcript chunk events from broker stream
      - Runs routing, suggestion, scoring
      - Acks message only if processing succeeds

    Notes:
      - Config + LLM provider come from the container (DI)
      - Routing runs first so it can set clarification suggestions; SuggestionEngine
        must not overwrite clarification suggestions (guard in SuggestionEngine)
    """
    container = build_container()

    broker = container["broker"]
    state = container["state_store"]
    llm = container["llm"]
    app_cfg = container["config"]

    semantic = container["semantic"]

    # Engines (config-driven)
    routing_engine = RoutingEngine(
        state=state,
        broker=broker,
        llm=llm,
        cfg=app_cfg,
        semantic=semantic,
    )
    suggestion_engine = SuggestionEngine(
        state=state,
        broker=broker,
        llm=llm,
        cfg=app_cfg,  # if you only need messages, pass app_cfg.messages instead
    )
    scoring_engine = ScoringEngine(
        state=state,
        broker=broker,
        cfg=app_cfg,
    )

    # Broker wiring
    stream = "transcript_chunks"
    group = "transcript_group"
    consumer = "worker-1"

    logger.info(
        "Transcript worker started (stream=%s group=%s consumer=%s)", stream, group, consumer
    )

    while True:
        messages = broker.consume(stream, group, consumer, count=10, block_ms=2000)

        for msg in messages:
            call_id = msg["call_id"]
            message_id = msg["_message_id"]
            trace_id = msg.get("trace_id")

            if not trace_id:
                payload = msg.get("payload")

                if isinstance(payload, dict):
                    trace_id = payload.get("trace_id")

                elif isinstance(payload, str) and payload:
                    try:
                        payload_obj = json.loads(payload)
                        if isinstance(payload_obj, dict):
                            trace_id = payload_obj.get("trace_id")
                    except Exception:
                        trace_id = None

            try:
                routing_engine.handle_call(call_id, trace_id=trace_id)
                suggestion_engine.handle_call(call_id, trace_id=trace_id)
                scoring_engine.handle_call(call_id, trace_id=trace_id)

                broker.ack(stream, group, message_id)
                logger.info("Processed chunk (call_id=%s msg_id=%s)", call_id, message_id)
            except Exception:
                # Do not ack => message will be re-delivered
                logger.exception(
                    "Worker error — not acking message (call_id=%s msg_id=%s)", call_id, message_id
                )

        time.sleep(0.05)


if __name__ == "__main__":
    run_transcript_worker()
