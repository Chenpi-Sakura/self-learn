from qdrant_client import AsyncQdrantClient
from selflearn.config import get_settings

_settings = get_settings()
_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=_settings.qdrant_url)
    return _client


async def health() -> bool:
    try:
        await get_qdrant().get_collections()
        return True
    except Exception:
        return False