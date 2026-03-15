from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    record_type: str
    record_date: date
    title: str
    notes: Optional[str] = None


class RecordCreateBatch(BaseModel):
    records: list[RecordCreate] = Field(..., min_length=1, max_length=100)


class RecordResponse(BaseModel):
    id: int
    user_id: int
    record_type: str
    record_date: date
    title: str
    notes: Optional[str]
    file_name: Optional[str]
    file_url: Optional[str]
    file_size: Optional[int]
    file_uploaded_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UploadRecordsResponse(BaseModel):
    created: int
    record_ids: list[int]


class PresignedUploadRequest(BaseModel):
    record_id: int
    file_name: str
    content_type: str


class PresignedUploadResponse(BaseModel):
    presigned_url: str
    s3_key: str
    expires_in: int


class FileUploadConfirmation(BaseModel):
    record_id: int
    s3_key: str
    file_name: str


class FileUploadConfirmationResponse(BaseModel):
    success: bool
    message: str
    file_url: Optional[str] = None


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_url: str
    file_size: int


class RecordListResponse(BaseModel):
    records: list[RecordResponse]
    total: int
    page: int
    limit: int
