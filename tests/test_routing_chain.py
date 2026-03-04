from types import SimpleNamespace

from voice_demo.app.use_cases.routing import RoutingEngine
from voice_demo.domain.constants import Route


class DummyState:
    def __init__(self, session):
        self._session = session

    def get_session(self, call_id):
        return self._session

    def save_session(self, session):
        self._session = session


class DummyBroker:
    def publish(self, *args, **kwargs):
        pass


class DummyLLM:
    def classify_intent(self, transcript: str):
        raise AssertionError("LLM should not be called in keyword test")


class DummySemantic:
    def rank_intents(self, transcript: str):
        raise AssertionError("Semantic should not be called in keyword test")


class RecordingLLM:
    def __init__(self):
        self.called = False

    def classify_intent(self, transcript: str):
        self.called = True
        return "SUPPORT", 0.9


def build_session(text: str, last_seq: int = 0):
    return SimpleNamespace(
        last_seq=last_seq,
        latest_suggestion=None,
        latest_route=None,
        latest_trace_id=None,
        transcript_text=lambda: text,
    )


def test_keyword_routing_short_circuits(app_config):
    session = build_session("you charged my card twice")

    engine = RoutingEngine(
        state=DummyState(session),
        broker=DummyBroker(),
        llm=DummyLLM(),
        semantic=DummySemantic(),
        cfg=app_config,
    )

    engine.handle_call("c1")

    assert session.latest_route.route == Route.BILLING
    assert "keyword_match" in session.latest_route.reason


def test_llm_not_called_below_threshold(app_config):
    session = build_session("something unclear", last_seq=0)

    llm = RecordingLLM()

    engine = RoutingEngine(
        state=DummyState(session),
        broker=DummyBroker(),
        llm=llm,
        semantic=DummySemantic(),
        cfg=app_config,
    )

    engine.handle_call("c1")

    assert llm.called is False
    assert session.latest_route.route == Route.UNKNOWN


def test_clarification_triggers_after_threshold(app_config):
    session = build_session("unclear message", last_seq=3)

    engine = RoutingEngine(
        state=DummyState(session),
        broker=DummyBroker(),
        llm=DummyLLM(),
        semantic=DummySemantic(),
        cfg=app_config,
    )

    engine.handle_call("c1")

    assert session.latest_route.route == Route.UNKNOWN
    assert session.latest_suggestion is not None
    assert "clarification" in session.latest_suggestion.rationale


def test_trace_id_saved(app_config):
    session = build_session("charged twice")

    engine = RoutingEngine(
        state=DummyState(session),
        broker=DummyBroker(),
        llm=DummyLLM(),
        semantic=DummySemantic(),
        cfg=app_config,
    )

    engine.handle_call("c1", trace_id="abc-123")

    assert session.latest_trace_id == "abc-123"
