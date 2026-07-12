import asyncio
from minio import Minio
from minio.error import S3Error
from selflearn.config import get_settings

_settings = get_settings()
_client: Minio | None = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(_settings.minio_endpoint,
                        access_key=_settings.minio_access_key,
                        secret_key=_settings.minio_secret_key,
                        secure=False)
    return _client


async def ensure_bucket() -> None:
    def _ensure() -> None:
        c = get_minio()
        if not c.bucket_exists(_settings.minio_bucket):
            c.make_bucket(_settings.minio_bucket)
    await asyncio.to_thread(_ensure)


async def health() -> bool:
    try:
        return await asyncio.to_thread(get_minio().bucket_exists, _settings.minio_bucket)
    except S3Error:
        return False
    except Exception:
        return False