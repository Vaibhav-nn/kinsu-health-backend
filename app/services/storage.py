import os
import uuid
from pathlib import Path
from typing import Dict

from app.config import settings


class FileStorageService:
    def __init__(self):
        self.storage_dir = Path(settings.file_storage_path)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def generate_upload_path(
        self,
        file_name: str,
        record_id: uuid.UUID,
    ) -> Dict[str, str]:
        file_extension = ""
        if "." in file_name:
            file_extension = file_name.rsplit(".", 1)[1]
        
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        record_dir = self.storage_dir / str(record_id)
        record_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = record_dir / unique_filename
        relative_path = f"{record_id}/{unique_filename}"
        file_url = f"{settings.base_url}/vault/files/{relative_path}"
        
        return {
            "file_path": str(file_path),
            "relative_path": relative_path,
            "file_url": file_url,
        }

    def save_file(self, file_path: str, content: bytes) -> int:
        with open(file_path, "wb") as f:
            f.write(content)
        return len(content)

    def verify_file_exists(self, relative_path: str) -> bool:
        file_path = self.storage_dir / relative_path
        return file_path.exists()

    def get_file_size(self, relative_path: str) -> int:
        file_path = self.storage_dir / relative_path
        return os.path.getsize(file_path)

    def get_file_content(self, relative_path: str) -> bytes:
        file_path = self.storage_dir / relative_path
        with open(file_path, "rb") as f:
            return f.read()


storage_service = FileStorageService()
