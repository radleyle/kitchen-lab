"""Shared constants and the storage interface both backends implement."""

from typing import Protocol

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class Storage(Protocol):
    def save(self, user_id: int, content_type: str, data: bytes) -> str: ...
    def load(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
