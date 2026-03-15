from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
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
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/records", response_model=RecordListResponse)
async def get_records(
    record_type: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordListResponse:
    logger.debug(
        "Fetching health records",
        extra={"extra_fields": {"record_type": record_type, "page": page, "limit": limit, "user_id": user.id}},
    )
    
    offset = (page - 1) * limit
    
    query = select(HealthRecord).where(HealthRecord.user_id == user.id).order_by(HealthRecord.record_date.desc())
    
    if record_type:
        query = query.where(HealthRecord.record_type == record_type)
    
    count_query = select(HealthRecord).where(HealthRecord.user_id == user.id)
    if record_type:
        count_query = count_query.where(HealthRecord.record_type == record_type)
    
    result = await db.execute(query.offset(offset).limit(limit))
    records = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    logger.info(
        "Health records retrieved",
        extra={"extra_fields": {"count": len(records), "total": total, "page": page, "user_id": user.id}},
    )
    
    return RecordListResponse(
        records=[RecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/records", response_model=UploadRecordsResponse)
async def upload_records(
    body: RecordCreateBatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadRecordsResponse:
    logger.info(
        "Creating health records",
        extra={"extra_fields": {"count": len(body.records), "user_id": user.id}},
    )
    
    records = [
        HealthRecord(
            user_id=user.id,
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
    
    logger.info(
        "Health records created successfully",
        extra={"extra_fields": {"count": len(ids), "user_id": user.id}},
    )
    
    return UploadRecordsResponse(created=len(ids), record_ids=ids)


@router.post("/records/{record_id}/upload", response_model=FileUploadResponse)
async def upload_file_direct(
    record_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileUploadResponse:
    logger.info(
        "Direct file upload initiated",
        extra={
            "extra_fields": {
                "record_id": record_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "user_id": user.id,
            }
        },
    )
    
    result = await db.execute(
        select(HealthRecord).where(
            HealthRecord.id == record_id,
            HealthRecord.user_id == user.id
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        logger.warning(
            "Health record not found for upload", 
            extra={"extra_fields": {"record_id": record_id, "user_id": user.id}}
        )
        raise HTTPException(status_code=404, detail="Health record not found")
    
    if settings.STORAGE_BACKEND == "local":
        upload_info = storage_service.generate_upload_path(
            file_name=file.filename,
            record_id=str(record_id),
        )
        
        content = await file.read()
        file_size = storage_service.save_file(upload_info["file_path"], content)
        
        record.file_name = file.filename
        record.file_url = upload_info["file_url"]
        record.file_size = file_size
        record.file_uploaded_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "File uploaded successfully",
            extra={
                "extra_fields": {
                    "record_id": record_id,
                    "filename": file.filename,
                    "file_size": file_size,
                    "user_id": user.id,
                }
            },
        )
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            file_url=upload_info["file_url"],
            file_size=file_size,
        )
    else:
        raise HTTPException(status_code=501, detail="S3 upload via direct endpoint not supported. Use presigned URL flow.")


@router.get("/files/{record_id}/{filename}")
async def download_file(
    record_id: int,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(
        "File download requested",
        extra={"extra_fields": {"record_id": record_id, "filename": filename, "user_id": user.id}},
    )
    
    # Verify the record belongs to the user
    result = await db.execute(
        select(HealthRecord).where(
            HealthRecord.id == record_id,
            HealthRecord.user_id == user.id
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        logger.warning(
            "Health record not found or unauthorized",
            extra={"extra_fields": {"record_id": record_id, "user_id": user.id}},
        )
        raise HTTPException(status_code=404, detail="Health record not found")
    
    if settings.STORAGE_BACKEND == "local":
        relative_path = f"{record_id}/{filename}"
        
        if not storage_service.verify_file_exists(relative_path):
            logger.warning(
                "File not found for download",
                extra={"extra_fields": {"record_id": record_id, "filename": filename}},
            )
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = storage_service.storage_dir / relative_path
        
        # Determine media type
        media_type = "application/pdf" if filename.lower().endswith('.pdf') else None
        
        # Create FileResponse with inline disposition (preview, not download)
        response = FileResponse(
            path=file_path,
            media_type=media_type,
        )
        
        # Set Content-Disposition to inline to show in browser, not download
        response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        logger.info(
            "File served successfully",
            extra={"extra_fields": {"record_id": record_id, "filename": filename, "user_id": user.id}},
        )
        
        return response
    else:
        raise HTTPException(status_code=501, detail="Direct file download not supported with S3. Use presigned download URL.")


@router.options("/files/{record_id}/{filename}")
async def download_file_options(record_id: str, filename: str):
    """Handle CORS preflight for file downloads"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("/records/upload-url", response_model=PresignedUploadResponse)
async def get_upload_url(
    body: PresignedUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    if settings.STORAGE_BACKEND == "local":
        raise HTTPException(
            status_code=400, 
            detail="Presigned URLs not supported with local storage. Use POST /records/{record_id}/upload instead"
        )
    
    logger.info(
        "Generating presigned upload URL",
        extra={
            "extra_fields": {
                "record_id": body.record_id,
                "filename": body.file_name,
                "user_id": user.id,
            }
        },
    )
    
    result = await db.execute(
        select(HealthRecord).where(
            HealthRecord.id == body.record_id,
            HealthRecord.user_id == user.id
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        logger.warning(
            "Health record not found for presigned URL", 
            extra={"extra_fields": {"record_id": body.record_id, "user_id": user.id}}
        )
        raise HTTPException(status_code=404, detail="Health record not found")
    
    try:
        presigned_data = s3_service.generate_presigned_upload_url(
            file_name=body.file_name,
            content_type=body.content_type,
            record_id=body.record_id,
        )
        
        logger.info(
            "Presigned upload URL generated",
            extra={"extra_fields": {"record_id": body.record_id, "s3_key": presigned_data["s3_key"], "user_id": user.id}},
        )
        
        return PresignedUploadResponse(
            presigned_url=presigned_data["presigned_url"],
            s3_key=presigned_data["s3_key"],
            expires_in=settings.S3_PRESIGNED_URL_EXPIRATION,
        )
    except Exception as e:
        logger.exception(
            "Failed to generate presigned upload URL",
            extra={"extra_fields": {"record_id": body.record_id, "error": str(e)}},
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.post("/records/confirm-upload", response_model=FileUploadConfirmationResponse)
async def confirm_file_upload(
    body: FileUploadConfirmation,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileUploadConfirmationResponse:
    if settings.STORAGE_BACKEND == "local":
        raise HTTPException(
            status_code=400,
            detail="Confirm upload not needed with local storage. Use POST /records/{record_id}/upload instead"
        )
    
    logger.info(
        "Confirming file upload",
        extra={
            "extra_fields": {
                "record_id": body.record_id,
                "s3_key": body.s3_key,
                "user_id": user.id,
            }
        },
    )
    
    result = await db.execute(
        select(HealthRecord).where(
            HealthRecord.id == body.record_id,
            HealthRecord.user_id == user.id
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        logger.warning(
            "Health record not found for upload confirmation", 
            extra={"extra_fields": {"record_id": body.record_id, "user_id": user.id}}
        )
        raise HTTPException(status_code=404, detail="Health record not found")
    
    if not s3_service.verify_file_exists(body.s3_key):
        logger.error(
            "File not found in S3 after upload",
            extra={"extra_fields": {"s3_key": body.s3_key, "record_id": body.record_id}},
        )
        raise HTTPException(status_code=400, detail="File not found in S3")
    
    try:
        file_size = s3_service.get_file_size(body.s3_key)
    except Exception as e:
        logger.exception(
            "Failed to get file info from S3",
            extra={"extra_fields": {"s3_key": body.s3_key, "error": str(e)}},
        )
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")
    
    file_url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{body.s3_key}"
    record.file_name = body.file_name
    record.file_url = file_url
    record.file_size = file_size
    record.file_uploaded_at = datetime.utcnow()
    
    await db.flush()
    
    logger.info(
        "File upload confirmed and metadata saved",
        extra={
            "extra_fields": {
                "record_id": body.record_id,
                "file_size": file_size,
                "s3_key": body.s3_key,
                "user_id": user.id,
            }
        },
    )
    
    return FileUploadConfirmationResponse(
        success=True,
        message="File upload confirmed and metadata saved",
        file_url=file_url,
    )
