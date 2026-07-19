"""File storage for experiment/notebook photos.

STORAGE_BACKEND=local  -> disk (Compose)
STORAGE_BACKEND=s3     -> S3 bucket (ECS task role provides credentials)
"""

from app.core.config import settings
from app.storage.base import Storage
from app.storage.local import LocalStorage

_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        backend = (settings.storage_backend or "local").lower()
        if backend == "s3":
            from app.storage.s3 import S3Storage

            _storage = S3Storage()
        elif backend == "local":
            _storage = LocalStorage()
        else:
            raise RuntimeError(
                f"Unknown STORAGE_BACKEND={backend!r}; use 'local' or 's3'"
            )
    return _storage


__all__ = ["LocalStorage", "get_storage", "Storage"]
