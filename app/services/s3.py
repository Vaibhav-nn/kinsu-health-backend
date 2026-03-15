import uuid
from typing import Dict

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3Service:
    def __init__(self):
        logger.info(
            "Initializing S3Service",
            extra={
                "extra_fields": {
                    "bucket_name": settings.S3_BUCKET_NAME,
                    "region": settings.AWS_REGION,
                }
            },
        )
        
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        logger.info("S3Service initialized successfully")

    def generate_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        record_id: uuid.UUID,
    ) -> Dict[str, str]:
        logger.info(
            "Generating presigned upload URL",
            extra={
                "extra_fields": {
                    "record_id": str(record_id),
                    "filename": file_name,
                    "content_type": content_type,
                }
            },
        )
        
        file_extension = ""
        if "." in file_name:
            file_extension = file_name.rsplit(".", 1)[1]
        
        s3_key = f"health-records/{record_id}/{uuid.uuid4()}.{file_extension}" if file_extension else f"health-records/{record_id}/{uuid.uuid4()}"
        
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRATION,
            )
            
            file_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.debug(
                "Presigned upload URL generated",
                extra={"extra_fields": {"s3_key": s3_key, "expires_in": settings.S3_PRESIGNED_URL_EXPIRATION}},
            )
            
            return {
                "presigned_url": presigned_url,
                "s3_key": s3_key,
                "file_url": file_url,
            }
        except ClientError as e:
            logger.exception(
                "Failed to generate presigned upload URL",
                extra={"extra_fields": {"s3_key": s3_key, "error": str(e)}},
            )
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def generate_presigned_download_url(self, s3_key: str) -> str:
        logger.info("Generating presigned download URL", extra={"extra_fields": {"s3_key": s3_key}})
        
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRATION,
            )
            logger.debug("Presigned download URL generated", extra={"extra_fields": {"s3_key": s3_key}})
            return presigned_url
        except ClientError as e:
            logger.exception(
                "Failed to generate presigned download URL",
                extra={"extra_fields": {"s3_key": s3_key, "error": str(e)}},
            )
            raise Exception(f"Failed to generate presigned download URL: {str(e)}")

    def verify_file_exists(self, s3_key: str) -> bool:
        logger.debug("Verifying file exists in S3", extra={"extra_fields": {"s3_key": s3_key}})
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            logger.debug("File exists in S3", extra={"extra_fields": {"s3_key": s3_key}})
            return True
        except ClientError as e:
            logger.warning(
                "File does not exist in S3",
                extra={"extra_fields": {"s3_key": s3_key, "error": str(e)}},
            )
            return False

    def get_file_size(self, s3_key: str) -> int:
        logger.debug("Getting file size from S3", extra={"extra_fields": {"s3_key": s3_key}})
        
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            size = response["ContentLength"]
            logger.debug(
                "File size retrieved from S3",
                extra={"extra_fields": {"s3_key": s3_key, "size_bytes": size}},
            )
            return size
        except ClientError as e:
            logger.exception(
                "Failed to get file size from S3",
                extra={"extra_fields": {"s3_key": s3_key, "error": str(e)}},
            )
            raise Exception(f"Failed to get file size: {str(e)}")


s3_service = S3Service()
