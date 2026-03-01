from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Single health record to upload."""

    record_type: str = Field(..., description="Type of record, e.g. lab_report, prescription, scan, note")
    record_date: date = Field(..., description="Date of the record")
    title: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=5000)


class RecordCreateBatch(BaseModel):
    """Request body for uploading multiple records."""

    records: list[RecordCreate] = Field(..., min_length=1, max_length=100)


class RecordResponse(BaseModel):
    """A created record as returned by the API."""

    id: UUID
    record_type: str
    record_date: date
    title: str
    notes: Optional[str]

    model_config = {"from_attributes": True}


class UploadRecordsResponse(BaseModel):
    """Response after uploading records."""

    created: int
    record_ids: list[UUID]
