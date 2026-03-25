"""Vault endpoints for records and file uploads."""

from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.api.deps import verify_firebase_token
from app.core.config import settings
from app.core.database import get_db
from app.models.vault import HealthRecord
from app.schemas.vault import (
    FileUploadConfirmation,
    FileUploadConfirmationResponse,
    FileUploadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    RecordCreateBatch,
    RecordListResponse,
    RecordResponse,
    UploadRecordsResponse,
)
from app.services.s3 import s3_service
from app.services.storage import storage_service

router = APIRouter(prefix="/vault", tags=["Vault"])


@router.get("/records", response_model=RecordListResponse)
async def list_records(
    record_type: Optional[str] = None,
    q: Optional[str] = Query(default=None, min_length=1, max_length=120),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    has_file: Optional[bool] = None,
    sort_by: Literal["record_date", "title", "file_uploaded_at"] = "record_date",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> RecordListResponse:
    """List vault records with optional type filter."""
    offset = (page - 1) * limit
    query = db.query(HealthRecord)

    if record_type:
        query = query.filter(HealthRecord.record_type == record_type)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                HealthRecord.title.ilike(pattern),
                HealthRecord.notes.ilike(pattern),
            )
        )
    if start_date:
        query = query.filter(HealthRecord.record_date >= start_date)
    if end_date:
        query = query.filter(HealthRecord.record_date <= end_date)
    if has_file is True:
        query = query.filter(HealthRecord.file_url.is_not(None))
    elif has_file is False:
        query = query.filter(HealthRecord.file_url.is_(None))

    sort_column_map = {
        "record_date": HealthRecord.record_date,
        "title": HealthRecord.title,
        "file_uploaded_at": HealthRecord.file_uploaded_at,
    }
    sort_column = sort_column_map[sort_by]
    sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)

    total = query.count()
    records = (
        query.order_by(sort_expression, desc(HealthRecord.record_date))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return RecordListResponse(
        records=[RecordResponse.model_validate(record) for record in records],
        total=total,
        page=page,
        limit=limit,
    )


@router.post(
    "/records",
    response_model=UploadRecordsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_records(
    body: RecordCreateBatch,
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> UploadRecordsResponse:
    """Create one or more record metadata entries."""
    records = [
        HealthRecord(
            record_type=item.record_type,
            record_date=item.record_date,
            title=item.title,
            notes=item.notes,
        )
        for item in body.records
    ]
    db.add_all(records)
    db.commit()

    return UploadRecordsResponse(
        created=len(records),
        record_ids=[record.id for record in records],
    )


@router.post("/records/upload-url", response_model=PresignedUploadResponse)
async def get_upload_url(
    body: PresignedUploadRequest,
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> PresignedUploadResponse:
    """Generate a presigned upload URL (S3 mode only)."""
    if settings.STORAGE_BACKEND == "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Presigned URLs not supported with local storage. "
                "Use POST /api/v1/vault/records/{record_id}/upload."
            ),
        )

    record = db.query(HealthRecord).filter(HealthRecord.id == body.record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found.")

    try:
        presigned_data = s3_service.generate_presigned_upload_url(
            file_name=body.file_name,
            content_type=body.content_type,
            record_id=body.record_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {exc}",
        ) from exc

    return PresignedUploadResponse(
        presigned_url=presigned_data["presigned_url"],
        s3_key=presigned_data["s3_key"],
        expires_in=settings.S3_PRESIGNED_URL_EXPIRATION,
    )


@router.post("/records/confirm-upload", response_model=FileUploadConfirmationResponse)
async def confirm_upload(
    body: FileUploadConfirmation,
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> FileUploadConfirmationResponse:
    """Confirm uploaded file metadata (S3 mode only)."""
    if settings.STORAGE_BACKEND == "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Confirm upload not needed with local storage. "
                "Use POST /api/v1/vault/records/{record_id}/upload."
            ),
        )

    record = db.query(HealthRecord).filter(HealthRecord.id == body.record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found.")

    if not s3_service.verify_file_exists(body.s3_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File not found in S3.")

    try:
        file_size = s3_service.get_file_size(body.s3_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read uploaded file metadata: {exc}",
        ) from exc

    file_url = (
        f"https://{settings.S3_BUCKET_NAME}.s3."
        f"{settings.AWS_REGION}.amazonaws.com/{body.s3_key}"
    )
    record.file_name = body.file_name
    record.file_url = file_url
    record.file_size = file_size
    record.file_uploaded_at = datetime.now(timezone.utc)
    db.commit()

    return FileUploadConfirmationResponse(
        success=True,
        message="File upload confirmed and metadata saved.",
        file_url=file_url,
    )


@router.post("/records/{record_id}/upload", response_model=FileUploadResponse)
async def upload_file_direct(
    record_id: str,
    file: UploadFile = File(...),
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    """Upload a file directly and attach it to a record (local mode)."""
    record = db.query(HealthRecord).filter(HealthRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found.")

    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Direct upload endpoint is only supported with local storage.",
        )

    file_name = file.filename or "upload.bin"
    upload_info = storage_service.generate_upload_path(file_name=file_name, record_id=record_id)
    content = await file.read()
    file_size = storage_service.save_file(upload_info["file_path"], content)

    record.file_name = file_name
    record.file_url = upload_info["file_url"]
    record.file_size = file_size
    record.file_uploaded_at = datetime.now(timezone.utc)
    db.commit()

    return FileUploadResponse(
        success=True,
        message="File uploaded successfully.",
        file_url=upload_info["file_url"],
        file_size=file_size,
    )


@router.get("/records/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: str,
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> RecordResponse:
    """Get one record by id."""
    record = db.query(HealthRecord).filter(HealthRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found.")
    return RecordResponse.model_validate(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: str,
    _decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> None:
    """Delete one record by id."""
    record = db.query(HealthRecord).filter(HealthRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found.")
    db.delete(record)
    db.commit()


@router.get("/files/{record_id}/{filename}")
async def download_file(
    record_id: str,
    filename: str,
    _decoded_token: dict = Depends(verify_firebase_token),
):
    """Download a locally stored file by record and filename."""
    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Direct file download is only supported with local storage.",
        )

    relative_path = f"{record_id}/{filename}"
    if not storage_service.verify_file_exists(relative_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    file_path = storage_service.storage_dir / relative_path
    return FileResponse(path=file_path, filename=filename)
