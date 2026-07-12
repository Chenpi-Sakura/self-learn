import redis.asyncio as redis
from selflearn.config import get_settings

_settings = get_settings()
_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(_settings.redis_url, decode_responses=True)
    return _client


async def health() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False