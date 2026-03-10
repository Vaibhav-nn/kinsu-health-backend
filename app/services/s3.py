import uuid
from typing import Dict

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.s3_bucket_name

    def generate_presigned_upload_url(
        self,
        file_name: str,
        content_type: str,
        record_id: uuid.UUID,
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
                ExpiresIn=settings.s3_presigned_url_expiration,
            )
            
            file_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            
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
                ExpiresIn=settings.s3_presigned_url_expiration,
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
