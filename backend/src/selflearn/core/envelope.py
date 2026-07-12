from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ActorRef(BaseModel):
    type: str
    id: str


def _gen_trace_id() -> str:
    return str(uuid4())


def _gen_span_id() -> str:
    return uuid4().hex[:16]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Envelope(BaseModel):
    trace_id: str = Field(default_factory=_gen_trace_id)
    parent_id: str | None = None
    span_id: str = Field(default_factory=_gen_span_id)
    action: str
    sender: ActorRef
    target: ActorRef
    payload: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)
    retry_count: int = 0