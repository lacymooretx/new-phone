import io
from datetime import timedelta

import structlog
from minio import Minio
from minio.error import S3Error

from new_phone.config import settings

logger = structlog.get_logger()


class StorageService:
    def __init__(self):
        self.client: Minio | None = None
        self.bucket = settings.minio_bucket
        self.cold_bucket = settings.minio_archive_bucket

    async def init(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        try:
            for bucket_name in (self.bucket, self.cold_bucket):
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info("minio_bucket_created", bucket=bucket_name)
                else:
                    logger.info("minio_bucket_exists", bucket=bucket_name)
        except S3Error as e:
            logger.error("minio_init_failed", error=str(e))
            raise

    def upload_file(
        self, object_name: str, file_path: str, content_type: str = "audio/wav"
    ) -> bool:
        if not self.client:
            logger.error("minio_not_initialized")
            return False
        try:
            self.client.fput_object(self.bucket, object_name, file_path, content_type=content_type)
            logger.info("minio_upload_success", object_name=object_name)
            return True
        except S3Error as e:
            logger.error("minio_upload_failed", object_name=object_name, error=str(e))
            return False

    def upload_bytes(self, object_name: str, data: bytes, content_type: str = "audio/wav") -> bool:
        if not self.client:
            logger.error("minio_not_initialized")
            return False
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info("minio_upload_success", object_name=object_name)
            return True
        except S3Error as e:
            logger.error("minio_upload_failed", object_name=object_name, error=str(e))
            return False

    def presigned_url(self, object_name: str, expires: int = 300) -> str | None:
        if not self.client:
            return None
        try:
            return self.client.presigned_get_object(
                self.bucket, object_name, expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            logger.error("minio_presigned_failed", object_name=object_name, error=str(e))
            return None

    def delete_object(self, object_name: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error as e:
            logger.error("minio_delete_failed", object_name=object_name, error=str(e))
            return False

    def object_exists(self, object_name: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def copy_object(
        self,
        src_bucket: str,
        src_path: str,
        dst_bucket: str,
        dst_path: str,
    ) -> bool:
        if not self.client:
            logger.error("minio_not_initialized")
            return False
        try:
            from minio.commonconfig import CopySource

            self.client.copy_object(
                dst_bucket,
                dst_path,
                CopySource(src_bucket, src_path),
            )
            logger.info(
                "minio_copy_success",
                src=f"{src_bucket}/{src_path}",
                dst=f"{dst_bucket}/{dst_path}",
            )
            return True
        except S3Error as e:
            logger.error(
                "minio_copy_failed",
                src=f"{src_bucket}/{src_path}",
                dst=f"{dst_bucket}/{dst_path}",
                error=str(e),
            )
            return False

    def delete_object_from_bucket(self, bucket: str, object_name: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except S3Error as e:
            logger.error(
                "minio_delete_failed", bucket=bucket, object_name=object_name, error=str(e)
            )
            return False

    def presigned_url_from_bucket(
        self, bucket: str, object_name: str, expires: int = 300
    ) -> str | None:
        if not self.client:
            return None
        try:
            return self.client.presigned_get_object(
                bucket, object_name, expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            logger.error(
                "minio_presigned_failed", bucket=bucket, object_name=object_name, error=str(e)
            )
            return None
