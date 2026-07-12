"""Unit tests for Envelope / ActorRef."""
from selflearn.core.envelope import ActorRef, Envelope


def test_envelope_default_ids() -> None:
    env = Envelope(action="skill.execute",
                   sender=ActorRef(type="gateway", id="gw-1"),
                   target=ActorRef(type="skill", id="skill.ping"))
    assert env.trace_id
    assert env.span_id
    assert env.retry_count == 0


def test_envelope_round_trip() -> None:
    env = Envelope(action="skill.execute",
                   sender=ActorRef(type="agent", id="ping-01"),
                   target=ActorRef(type="skill", id="skill.ping"),
                   payload={"x": 1})
    restored = Envelope.model_validate_json(env.model_dump_json())
    assert restored.payload == {"x": 1}