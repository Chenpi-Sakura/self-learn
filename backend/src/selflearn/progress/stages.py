"""Stage 枚举 + ProgressEvent 数据类。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Stage(str, Enum):
    PROFILE = "profile"
    PLAN = "plan"
    DIRECTOR = "director"
    EXERCISE = "exercise"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    # Task 2：提炼主题 5 阶段流水线
    EXTRACT_TOPICS_PARSE = "extract_topics.parse"
    EXTRACT_TOPICS_LLM = "extract_topics.llm"
    EXTRACT_TOPICS_VALIDATE = "extract_topics.validate"
    EXTRACT_TOPICS_WRITE = "extract_topics.write"
    EXTRACT_TOPICS_DONE = "extract_topics.done"


@dataclass
class ProgressEvent:
    stage: Stage
    status: str  # "running" | "completed" | "failed"
    payload: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_redis_fields(self) -> dict[str, str]:
        return {
            "stage": self.stage.value,
            "status": self.status,
            "payload": json.dumps(self.payload, ensure_ascii=False),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_redis_fields(cls, fields: dict[object, object]) -> "ProgressEvent":
        decoded: dict[str, str] = {}
        for k, v in fields.items():
            key = k.decode() if isinstance(k, bytes) else str(k)
            val = v.decode() if isinstance(v, bytes) else str(v)
            decoded[key] = val
        return cls(
            stage=Stage(decoded["stage"]),
            status=decoded["status"],
            payload=json.loads(decoded["payload"]),
            timestamp=datetime.fromisoformat(decoded["timestamp"]),
        )