"""Vitals endpoints — Log, list, get, delete, and trends."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

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

router = APIRouter(prefix="/vitals", tags=["Vitals"])


@router.post("/", response_model=VitalLogResponse, status_code=status.HTTP_201_CREATED)
async def log_vital(
    payload: VitalLogCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VitalLogResponse:
    """Log a new vital reading (heart rate, BP, SpO2, etc.)."""
    vital = VitalLog(user_id=user.id, **payload.model_dump())
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return VitalLogResponse.model_validate(vital)


@router.get("/", response_model=list[VitalLogResponse])
async def list_vitals(
    vital_type: Optional[str] = Query(None, description="Filter by vital type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VitalLogResponse]:
    """List vital readings with optional filters."""
    query = db.query(VitalLog).filter(VitalLog.user_id == user.id)

    if vital_type:
        query = query.filter(VitalLog.vital_type == vital_type)
    if start_date:
        query = query.filter(VitalLog.recorded_at >= start_date)
    if end_date:
        query = query.filter(VitalLog.recorded_at <= end_date)

    vitals = query.order_by(VitalLog.recorded_at.desc()).offset(offset).limit(limit).all()
    return model_list(vitals, VitalLogResponse)


@router.get("/trends", response_model=VitalTrendResponse)
async def vital_trends(
    vital_type: str = Query(..., description="Vital type to get trends for"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VitalTrendResponse:
    """Get aggregated trend data for a specific vital type (for charts)."""
    query = db.query(VitalLog).filter(
        VitalLog.user_id == user.id,
        VitalLog.vital_type == vital_type,
    )

    if start_date:
        query = query.filter(VitalLog.recorded_at >= start_date)
    if end_date:
        query = query.filter(VitalLog.recorded_at <= end_date)

    vitals = query.order_by(VitalLog.recorded_at.asc()).all()

    if not vitals:
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
    db: Session = Depends(get_db),
) -> VitalLogResponse:
    """Get a single vital reading by ID."""
    vital = get_user_owned_or_404(
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
    db: Session = Depends(get_db),
) -> None:
    """Delete a vital reading."""
    vital = get_user_owned_or_404(
        db,
        VitalLog,
        item_id=vital_id,
        user_id=user.id,
        not_found_detail="Vital log not found.",
    )
    db.delete(vital)
    db.commit()
