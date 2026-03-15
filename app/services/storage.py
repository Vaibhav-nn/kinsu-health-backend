import os
import uuid
from pathlib import Path
from typing import Dict, Union

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileStorageService:
    def __init__(self):
        self.storage_dir = Path(settings.FILE_STORAGE_PATH)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "FileStorageService initialized",
            extra={"extra_fields": {"storage_dir": str(self.storage_dir)}},
        )

    def generate_upload_path(
        self,
        file_name: str,
        record_id: Union[int, str],
    ) -> Dict[str, str]:
        file_extension = ""
        if "." in file_name:
            file_extension = file_name.rsplit(".", 1)[1]
        
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        record_dir = self.storage_dir / str(record_id)
        record_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = record_dir / unique_filename
        relative_path = f"{record_id}/{unique_filename}"
        file_url = f"{settings.BASE_URL}/vault/files/{relative_path}"
        
        logger.debug(
            "Generated upload path",
            extra={
                "extra_fields": {
                    "record_id": str(record_id),
                    "original_filename": file_name,
                    "unique_filename": unique_filename,
                }
            },
        )
        
        return {
            "file_path": str(file_path),
            "relative_path": relative_path,
            "file_url": file_url,
        }

    def save_file(self, file_path: str, content: bytes) -> int:
        logger.info(
            "Saving file to local storage",
            extra={"extra_fields": {"file_path": file_path, "size_bytes": len(content)}},
        )
        
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            logger.debug("File saved successfully", extra={"extra_fields": {"file_path": file_path}})
            return len(content)
        except Exception as e:
            logger.exception(
                "Failed to save file",
                extra={"extra_fields": {"file_path": file_path, "error": str(e)}},
            )
            raise

    def verify_file_exists(self, relative_path: str) -> bool:
        file_path = self.storage_dir / relative_path
        exists = file_path.exists()
        logger.debug(
            "File existence check",
            extra={"extra_fields": {"relative_path": relative_path, "exists": exists}},
        )
        return exists

    def get_file_size(self, relative_path: str) -> int:
        file_path = self.storage_dir / relative_path
        try:
            size = os.path.getsize(file_path)
            logger.debug(
                "Retrieved file size",
                extra={"extra_fields": {"relative_path": relative_path, "size_bytes": size}},
            )
            return size
        except Exception as e:
            logger.error(
                "Failed to get file size",
                extra={"extra_fields": {"relative_path": relative_path, "error": str(e)}},
            )
            raise

    def get_file_content(self, relative_path: str) -> bytes:
        file_path = self.storage_dir / relative_path
        logger.debug("Reading file content", extra={"extra_fields": {"relative_path": relative_path}})
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            logger.debug(
                "File content retrieved",
                extra={"extra_fields": {"relative_path": relative_path, "size_bytes": len(content)}},
            )
            return content
        except Exception as e:
            logger.exception(
                "Failed to read file content",
                extra={"extra_fields": {"relative_path": relative_path, "error": str(e)}},
            )
            raise


storage_service = FileStorageService()
