from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    record_type: str
    document_subtype: Optional[str] = None
    record_date: date
    title: str
    provider_name: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


class RecordCreateBatch(BaseModel):
    records: list[RecordCreate] = Field(..., min_length=1, max_length=100)


class RecordResponse(BaseModel):
    id: str
    family_member_id: Optional[int]
    record_type: str
    document_subtype: Optional[str]
    record_date: date
    title: str
    provider_name: Optional[str]
    tags: Optional[list[str]]
    notes: Optional[str]
    file_name: Optional[str]
    file_url: Optional[str]
    file_size: Optional[int]
    file_uploaded_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UploadRecordsResponse(BaseModel):
    created: int
    record_ids: list[str]


class PresignedUploadRequest(BaseModel):
    record_id: str
    file_name: str
    content_type: str


class PresignedUploadResponse(BaseModel):
    presigned_url: str
    upload_url: str
    s3_key: str
    expires_in: int


class FileUploadConfirmation(BaseModel):
    record_id: str
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


class ConnectedServiceResponse(BaseModel):
    id: int
    provider_name: str
    provider_type: str
    status: str
    record_count: int
    synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConnectedServiceUpsert(BaseModel):
    provider_name: str
    provider_type: str
    status: str = "pending"


class LabTrendPoint(BaseModel):
    observed_on: date
    value: float


class LabTrendHistoryItem(BaseModel):
    observed_on: date
    value: float
    unit: str


class LabParameterTrendResponse(BaseModel):
    parameter_key: str
    parameter_label: str
    unit: str
    latest_value: Optional[float] = None
    status: Optional[str] = None
    data_points: list[LabTrendPoint]
    history: list[LabTrendHistoryItem]
