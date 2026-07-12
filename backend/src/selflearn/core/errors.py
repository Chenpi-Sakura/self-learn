from enum import Enum


class ErrorCode(str, Enum):
    ENVELOPE_INVALID = "ENVELOPE_INVALID"
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_OVERLOAD = "AGENT_OVERLOAD"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_UPSTREAM = "LLM_UPSTREAM"
    DB_CONFLICT = "DB_CONFLICT"
    INTERNAL = "INTERNAL"
    # Stage 3: ExerciseAgent 1 次重试仍 lint 拒收 → 422 Unprocessable Entity
    EXERCISE_INVALID = "EXERCISE_INVALID"


_DEFAULT = {
    ErrorCode.ENVELOPE_INVALID: 400,
    ErrorCode.SKILL_NOT_FOUND: 422,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.AGENT_OVERLOAD: 503,
    ErrorCode.LLM_RATE_LIMIT: 429,
    ErrorCode.LLM_UPSTREAM: 502,
    ErrorCode.DB_CONFLICT: 409,
    ErrorCode.INTERNAL: 500,
    ErrorCode.EXERCISE_INVALID: 422,  # Unprocessable Entity
}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, http_status: int | None = None, **extra: object):
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.http_status = http_status or _DEFAULT[code]
        self.extra = extra

    def to_dict(self, trace_id: str | None = None) -> dict[str, object]:
        body: dict[str, object] = {"code": self.code.value, "message": self.message}
        if trace_id:
            body["trace_id"] = trace_id
        if self.extra:
            body["extra"] = self.extra
        return {"error": body}