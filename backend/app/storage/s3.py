"""S3-backed photo storage for production.

Keys keep the same shape as LocalStorage (attachments/{user_id}/{uuid}.ext)
so Attachment.s3_key rows work in both environments.
"""

import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.storage.base import ALLOWED_CONTENT_TYPES, MAX_BYTES


class S3Storage:
    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket = bucket or settings.s3_bucket
        if not self.bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        self.client = boto3.client(
            "s3",
            region_name=region or settings.aws_region or None,
        )

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
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def load(self, key: str) -> bytes:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                raise FileNotFoundError(key) from exc
            raise
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
