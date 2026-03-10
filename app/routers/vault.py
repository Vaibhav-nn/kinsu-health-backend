from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.vault import HealthRecord
from app.schemas.vault import (
    FileUploadConfirmation,
    FileUploadConfirmationResponse,
    FileUploadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    RecordCreateBatch,
    UploadRecordsResponse,
)
from app.services.s3 import s3_service
from app.services.storage import storage_service

router = APIRouter()


@router.post("/records", response_model=UploadRecordsResponse)
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
    await db.flush()
    ids = [r.id for r in records]
    return UploadRecordsResponse(created=len(ids), record_ids=ids)


@router.post("/records/{record_id}/upload", response_model=FileUploadResponse)
async def upload_file_direct(
    record_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> FileUploadResponse:
    result = await db.execute(
        select(HealthRecord).where(HealthRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    if settings.storage_backend == "local":
        upload_info = storage_service.generate_upload_path(
            file_name=file.filename,
            record_id=record_id,
        )
        
        content = await file.read()
        file_size = storage_service.save_file(upload_info["file_path"], content)
        
        record.file_name = file.filename
        record.file_url = upload_info["file_url"]
        record.file_size = file_size
        record.file_uploaded_at = datetime.utcnow()
        
        await db.flush()
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            file_url=upload_info["file_url"],
            file_size=file_size,
        )
    else:
        raise HTTPException(status_code=501, detail="S3 upload via direct endpoint not supported. Use presigned URL flow.")


@router.get("/files/{record_id}/{filename}")
async def download_file(record_id: str, filename: str):
    if settings.storage_backend == "local":
        relative_path = f"{record_id}/{filename}"
        
        if not storage_service.verify_file_exists(relative_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = storage_service.storage_dir / relative_path
        return FileResponse(path=file_path, filename=filename)
    else:
        raise HTTPException(status_code=501, detail="Direct file download not supported with S3. Use presigned download URL.")


@router.post("/records/upload-url", response_model=PresignedUploadResponse)
async def get_upload_url(
    body: PresignedUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    if settings.storage_backend == "local":
        raise HTTPException(
            status_code=400, 
            detail="Presigned URLs not supported with local storage. Use POST /records/{record_id}/upload instead"
        )
    
    result = await db.execute(
        select(HealthRecord).where(HealthRecord.id == body.record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    try:
        presigned_data = s3_service.generate_presigned_upload_url(
            file_name=body.file_name,
            content_type=body.content_type,
            record_id=body.record_id,
        )
        
        return PresignedUploadResponse(
            presigned_url=presigned_data["presigned_url"],
            s3_key=presigned_data["s3_key"],
            expires_in=settings.s3_presigned_url_expiration,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.post("/records/confirm-upload", response_model=FileUploadConfirmationResponse)
async def confirm_file_upload(
    body: FileUploadConfirmation,
    db: AsyncSession = Depends(get_db),
) -> FileUploadConfirmationResponse:
    if settings.storage_backend == "local":
        raise HTTPException(
            status_code=400,
            detail="Confirm upload not needed with local storage. Use POST /records/{record_id}/upload instead"
        )
    
    result = await db.execute(
        select(HealthRecord).where(HealthRecord.id == body.record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    if not s3_service.verify_file_exists(body.s3_key):
        raise HTTPException(status_code=400, detail="File not found in S3")
    
    try:
        file_size = s3_service.get_file_size(body.s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")
    
    file_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{body.s3_key}"
    record.file_name = body.file_name
    record.file_url = file_url
    record.file_size = file_size
    record.file_uploaded_at = datetime.utcnow()
    
    await db.flush()
    
    return FileUploadConfirmationResponse(
        success=True,
        message="File upload confirmed and metadata saved",
        file_url=file_url,
    )
