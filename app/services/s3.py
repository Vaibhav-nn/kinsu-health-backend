import uuid
from typing import Dict

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        record_id: str,
    ) -> Dict[str, str]:
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

            file_url = (
                f"https://{self.bucket_name}.s3."
                f"{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            )
            
            return {
                "presigned_url": presigned_url,
                "s3_key": s3_key,
                "file_url": file_url,
            }
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def generate_presigned_download_url(self, s3_key: str) -> str:
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRATION,
            )
            return presigned_url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned download URL: {str(e)}")

    def verify_file_exists(self, s3_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_file_size(self, s3_key: str) -> int:
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response["ContentLength"]
        except ClientError as e:
            raise Exception(f"Failed to get file size: {str(e)}")


s3_service = S3Service()
