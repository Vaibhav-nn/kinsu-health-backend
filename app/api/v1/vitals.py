"""Vitals endpoints — Log, list, get, delete, and trends."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1._utils import get_user_owned_or_404, model_list
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.vital import VitalLog
from app.schemas.health import (
    VitalLogCreate,
    VitalLogResponse,
    VitalTrendPoint,
    VitalTrendResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/vitals", tags=["Vitals"])


@router.post("/", response_model=VitalLogResponse, status_code=status.HTTP_201_CREATED)
async def log_vital(
    payload: VitalLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VitalLogResponse:
    """Log a new vital reading (heart rate, BP, SpO2, etc.)."""
    logger.info(
        "Logging new vital",
        extra={
            "extra_fields": {
                "user_id": str(user.id),
                "vital_type": payload.vital_type,
                "value": payload.value,
            }
        },
    )
    
    vital = VitalLog(user_id=user.id, **payload.model_dump())
    db.add(vital)
    await db.flush()
    await db.refresh(vital)
    
    logger.debug(
        "Vital logged successfully",
        extra={"extra_fields": {"vital_id": vital.id}},
    )
    
    return VitalLogResponse.model_validate(vital)


@router.get("/", response_model=list[VitalLogResponse])
async def list_vitals(
    vital_type: Optional[str] = Query(None, description="Filter by vital type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VitalLogResponse]:
    """List vital readings with optional filters."""
    logger.debug(
        "Listing vitals",
        extra={
            "extra_fields": {
                "user_id": str(user.id),
                "vital_type": vital_type,
                "limit": limit,
                "offset": offset,
            }
        },
    )
    
    query = select(VitalLog).where(VitalLog.user_id == user.id)

    if vital_type:
        query = query.where(VitalLog.vital_type == vital_type)
    if start_date:
        query = query.where(VitalLog.recorded_at >= start_date)
    if end_date:
        query = query.where(VitalLog.recorded_at <= end_date)

    result = await db.execute(
        query.order_by(VitalLog.recorded_at.desc()).offset(offset).limit(limit)
    )
    vitals = result.scalars().all()
    
    logger.info(
        "Vitals retrieved",
        extra={"extra_fields": {"count": len(vitals), "vital_type": vital_type}},
    )
    
    return model_list(vitals, VitalLogResponse)


@router.get("/trends", response_model=VitalTrendResponse)
async def vital_trends(
    vital_type: str = Query(..., description="Vital type to get trends for"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VitalTrendResponse:
    """Get aggregated trend data for a specific vital type (for charts)."""
    logger.debug(
        "Fetching vital trends",
        extra={"extra_fields": {"user_id": str(user.id), "vital_type": vital_type}},
    )
    
    query = select(VitalLog).where(
        VitalLog.user_id == user.id,
        VitalLog.vital_type == vital_type,
    )

    if start_date:
        query = query.where(VitalLog.recorded_at >= start_date)
    if end_date:
        query = query.where(VitalLog.recorded_at <= end_date)

    result = await db.execute(query.order_by(VitalLog.recorded_at.asc()))
    vitals = result.scalars().all()

    if not vitals:
        logger.info(
            "No vitals found for trend analysis",
            extra={"extra_fields": {"vital_type": vital_type}},
        )
        return VitalTrendResponse(
            vital_type=vital_type,
            unit="",
            data_points=[],
            count=0,
        )

    data_points = [
        VitalTrendPoint(
            recorded_at=v.recorded_at,
            value=v.value,
            value_secondary=v.value_secondary,
        )
        for v in vitals
    ]

    values = [v.value for v in vitals]

    logger.info(
        "Vital trends calculated",
        extra={
            "extra_fields": {
                "vital_type": vital_type,
                "count": len(vitals),
                "avg_value": round(sum(values) / len(values), 2),
            }
        },
    )

    return VitalTrendResponse(
        vital_type=vital_type,
        unit=vitals[0].unit,
        data_points=data_points,
        count=len(vitals),
        avg_value=round(sum(values) / len(values), 2),
        min_value=min(values),
        max_value=max(values),
    )


@router.get("/{vital_id}", response_model=VitalLogResponse)
async def get_vital(
    vital_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VitalLogResponse:
    """Get a single vital reading by ID."""
    logger.debug("Fetching vital by ID", extra={"extra_fields": {"vital_id": vital_id}})
    
    vital = await get_user_owned_or_404(
        db,
        VitalLog,
        item_id=vital_id,
        user_id=user.id,
        not_found_detail="Vital log not found.",
    )
    return VitalLogResponse.model_validate(vital)


@router.delete("/{vital_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vital(
    vital_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a vital reading."""
    logger.info(
        "Deleting vital",
        extra={"extra_fields": {"vital_id": vital_id, "user_id": str(user.id)}},
    )
    
    vital = await get_user_owned_or_404(
        db,
        VitalLog,
        item_id=vital_id,
        user_id=user.id,
        not_found_detail="Vital log not found.",
    )
    await db.delete(vital)
    await db.flush()
    
    logger.info("Vital deleted successfully", extra={"extra_fields": {"vital_id": vital_id}})