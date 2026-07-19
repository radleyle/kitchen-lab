"""Local filesystem storage for attachments (Docker Compose / laptop)."""

import uuid
from pathlib import Path

from app.core.config import settings
from app.storage.base import ALLOWED_CONTENT_TYPES, MAX_BYTES


class LocalStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.media_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, user_id: int, content_type: str, data: bytes) -> str:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported content type {content_type!r}. "
                f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
            )
        if len(data) > MAX_BYTES:
            raise ValueError(f"File too large (max {MAX_BYTES // (1024 * 1024)} MB)")
        if not data:
            raise ValueError("Empty file")

        ext = ALLOWED_CONTENT_TYPES[content_type]
        key = f"attachments/{user_id}/{uuid.uuid4().hex}{ext}"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key")
        return path

    def load(self, key: str) -> bytes:
        path = self.path_for(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self.path_for(key)
        if path.is_file():
            path.unlink()
