"""
SEPEHR Backend — MinIO Object Storage Infrastructure
"""

from __future__ import annotations

import io
import logging
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)


class StorageClient:
    """MinIO-backed object storage client."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._buckets = [
            settings.MINIO_BUCKET_MEDIA,
            settings.MINIO_BUCKET_VOICE,
            settings.MINIO_BUCKET_FILES,
        ]

    async def ensure_buckets(self) -> None:
        """Create buckets if they don't exist. Called on startup."""
        for bucket in self._buckets:
            try:
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
            except S3Error as e:
                logger.error(f"Failed to create bucket {bucket}: {e}")
                raise ServiceUnavailableException(f"Storage initialization failed: {e}")

    def upload_file(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file to MinIO.
        Returns the object key on success.
        """
        try:
            self._client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=metadata,
            )
            return object_key
        except S3Error as e:
            logger.error(f"MinIO upload error for {object_key}: {e}")
            raise ServiceUnavailableException("File upload failed")

    def get_presigned_url(
        self,
        bucket: str,
        object_key: str,
        expires_hours: int = 24,
    ) -> str:
        """Generate a presigned URL for temporary file access."""
        try:
            return self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_key,
                expires=timedelta(hours=expires_hours),
            )
        except S3Error as e:
            logger.error(f"MinIO presign error for {object_key}: {e}")
            raise ServiceUnavailableException("Could not generate file URL")

    def delete_file(self, bucket: str, object_key: str) -> None:
        """Delete a file from MinIO."""
        try:
            self._client.remove_object(bucket, object_key)
        except S3Error as e:
            logger.error(f"MinIO delete error for {object_key}: {e}")

    def delete_files(self, bucket: str, object_keys: list[str]) -> None:
        """Batch delete files from MinIO."""
        from minio.deleteobjects import DeleteObject

        objects = [DeleteObject(key) for key in object_keys]
        errors = self._client.remove_objects(bucket, iter(objects))
        for error in errors:
            logger.error(f"MinIO batch delete error: {error}")

    def file_exists(self, bucket: str, object_key: str) -> bool:
        """Check if a file exists in MinIO."""
        try:
            self._client.stat_object(bucket, object_key)
            return True
        except S3Error:
            return False

    def get_file_url(self, bucket: str, object_key: str) -> str:
        """
        Get the public URL for an object.
        Use presigned URL for private buckets.
        """
        return self.get_presigned_url(bucket, object_key)


storage = StorageClient()
