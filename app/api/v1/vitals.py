"""Vitals endpoints — Log, list, snapshots, summaries, delete, and trends."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404, model_list
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.user import User
from app.models.vital import VitalLog
from app.schemas.health import (
    VitalLogCreate,
    VitalLogResponse,
    VitalSnapshotCreate,
    VitalTodayCard,
    VitalTrendPoint,
    VitalTrendResponse,
)

router = APIRouter(prefix="/vitals", tags=["Vitals"])

_VITAL_META: dict[str, tuple[str, str]] = {
    "blood_pressure": ("Blood Pressure", "mmHg"),
    "blood_sugar": ("Blood Sugar", "mg/dL"),
    "heart_rate": ("Heart Rate", "bpm"),
    "weight": ("Weight", "kg"),
    "temperature": ("Temperature", "°F"),
    "spo2": ("SpO2", "%"),
}


def _latest_delta_label(entries: list[VitalLog]) -> str:
    if len(entries) < 2:
        return "→ 0%"
    latest = entries[0].value
    previous = entries[1].value
    if abs(previous) < 0.0001:
        return "→ 0%"
    delta = ((latest - previous) / previous) * 100
    if abs(delta) < 0.1:
        return "→ 0%"
    arrow = "↑" if delta > 0 else "↓"
    return f"{arrow} {abs(round(delta))}%"


def _display_value(vital: VitalLog) -> str:
    if vital.vital_type == "blood_pressure" and vital.value_secondary is not None:
        return f"{vital.value:g}/{vital.value_secondary:g}"
    return f"{vital.value:g}"


@router.post("", response_model=VitalLogResponse, status_code=status.HTTP_201_CREATED)
async def log_vital(
    payload: VitalLogCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> VitalLogResponse:
    """Log a new vital reading (heart rate, BP, SpO2, etc.)."""
    vital = VitalLog(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return VitalLogResponse.model_validate(vital)


@router.post("/snapshot", response_model=list[VitalLogResponse], status_code=status.HTTP_201_CREATED)
async def log_vital_snapshot(
    payload: VitalSnapshotCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[VitalLogResponse]:
    created: list[VitalLog] = []

    def add_vital(vital_type: str, value: float | None, unit: str, value_secondary: float | None = None) -> None:
        if value is None:
            return
        vital = VitalLog(
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
            vital_type=vital_type,
            value=value,
            value_secondary=value_secondary,
            unit=unit,
            recorded_at=payload.recorded_at,
            notes=payload.notes,
        )
        db.add(vital)
        created.append(vital)

    add_vital("blood_pressure", payload.blood_pressure_systolic, "mmHg", payload.blood_pressure_diastolic)
    add_vital("blood_sugar", payload.blood_sugar, "mg/dL")
    add_vital("heart_rate", payload.heart_rate, "bpm")
    add_vital("weight", payload.weight, "kg")
    add_vital("temperature", payload.temperature, "°F")
    add_vital("spo2", payload.spo2, "%")

    db.commit()
    for vital in created:
        db.refresh(vital)
    return [VitalLogResponse.model_validate(vital) for vital in created]


@router.get("", response_model=list[VitalLogResponse])
async def list_vitals(
    vital_type: Optional[str] = Query(None, description="Filter by vital type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[VitalLogResponse]:
    """List vital readings with optional filters."""
    query = apply_profile_scope(
        db.query(VitalLog),
        VitalLog,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )

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
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> VitalTrendResponse:
    """Get aggregated trend data for a specific vital type (for charts)."""
    query = apply_profile_scope(
        db.query(VitalLog),
        VitalLog,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    ).filter(VitalLog.vital_type == vital_type)

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


@router.get("/today-cards", response_model=list[VitalTodayCard])
async def today_vital_cards(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[VitalTodayCard]:
    cards: list[VitalTodayCard] = []
    for vital_type, (label, fallback_unit) in _VITAL_META.items():
        entries = (
            apply_profile_scope(
                db.query(VitalLog),
                VitalLog,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(VitalLog.vital_type == vital_type)
            .order_by(VitalLog.recorded_at.desc())
            .limit(2)
            .all()
        )
        if not entries:
            cards.append(
                VitalTodayCard(
                    vital_type=vital_type,
                    label=label,
                    latest_value="--",
                    unit=fallback_unit,
                    delta_label="→ 0%",
                )
            )
            continue

        cards.append(
            VitalTodayCard(
                vital_type=vital_type,
                label=label,
                latest_value=_display_value(entries[0]),
                unit=entries[0].unit or fallback_unit,
                delta_label=_latest_delta_label(entries),
            )
        )
    return cards


@router.get("/{vital_id}", response_model=VitalLogResponse)
async def get_vital(
    vital_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> VitalLogResponse:
    """Get a single vital reading by ID."""
    vital = get_user_owned_or_404(
        db,
        VitalLog,
        item_id=vital_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Vital log not found.",
    )
    return VitalLogResponse.model_validate(vital)


@router.delete("/{vital_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vital(
    vital_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    """Delete a vital reading."""
    vital = get_user_owned_or_404(
        db,
        VitalLog,
        item_id=vital_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Vital log not found.",
    )
    db.delete(vital)
    db.commit()
