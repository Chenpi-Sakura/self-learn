"""Unit tests for Envelope / ActorRef / bus."""
import json

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


def test_envelope_via_bus_serialization() -> None:
    """模拟 bus 的 JSON 编解码路径，验证 Envelope 兼容。"""
    env = Envelope(action="skill.execute",
                   sender=ActorRef(type="gateway", id="gw-1"),
                   target=ActorRef(type="skill", id="skill.ping"),
                   payload={"k": "v"})
    body = env.model_dump_json().encode("utf-8")
    payload = json.loads(body.decode("utf-8"))
    restored = Envelope.model_validate(payload)
    assert restored.trace_id == env.trace_id
    assert restored.payload == {"k": "v"}