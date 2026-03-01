from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.vault import HealthRecord
from app.schemas.vault import (
    RecordCreate,
    RecordCreateBatch,
    UploadRecordsResponse,
)

router = APIRouter()


@router.post(
    "/records",
    response_model=UploadRecordsResponse,
    summary="Upload health records",
    description="Upload one or more health records (metadata) to the vault. Returns created record IDs.",
)
async def upload_records(
    body: RecordCreateBatch,
    db: AsyncSession = Depends(get_db),
) -> UploadRecordsResponse:
    records = [
        HealthRecord(
            record_type=r.record_type,
            record_date=r.record_date,
            title=r.title,
            notes=r.notes,
        )
        for r in body.records
    ]
    db.add_all(records)
    await db.flush()  # Get IDs without committing (get_db commits)
    ids = [r.id for r in records]
    return UploadRecordsResponse(created=len(ids), record_ids=ids)
