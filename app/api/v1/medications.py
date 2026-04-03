"""Medications endpoints — CRUD operations and adherence summaries."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404, model_list
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.medication import Medication
from app.models.medication_dose_log import MedicationDoseLog
from app.models.user import User
from app.schemas.health import (
    MedicationAdherenceResponse,
    MedicationCreate,
    MedicationDashboardItem,
    MedicationDashboardResponse,
    MedicationDoseLogCreate,
    MedicationDoseLogResponse,
    MedicationMonthlyCalendarDay,
    MedicationResponse,
    MedicationUpdate,
    MedicationWeeklyMatrixEntry,
)

router = APIRouter(prefix="/medications", tags=["Medications"])


def _scoped_medication_query(db: Session, *, user_id: int, family_member_id: int | None):
    return apply_profile_scope(
        db.query(Medication),
        Medication,
        user_id=user_id,
        family_member_id=family_member_id,
    )


def _scoped_dose_query(db: Session, *, user_id: int, family_member_id: int | None):
    return apply_profile_scope(
        db.query(MedicationDoseLog),
        MedicationDoseLog,
        user_id=user_id,
        family_member_id=family_member_id,
    )


def _schedule_label(medication: Medication) -> str:
    frequency_map = {
        "once_daily": "Morning",
        "twice_daily": "Morning, evening",
        "weekly": "Weekly",
        "monthly": "Monthly",
        "as_needed": "SOS",
    }
    prefix = frequency_map.get(medication.frequency, medication.frequency.replace("_", " ").title())
    return f"{prefix} · {medication.dosage}"


def _ensure_today_dose_logs(
    db: Session,
    *,
    medication: Medication,
    user_id: int,
    family_member_id: int | None,
    target_date: date,
) -> list[MedicationDoseLog]:
    existing = (
        db.query(MedicationDoseLog)
        .filter(
            MedicationDoseLog.user_id == user_id,
            MedicationDoseLog.medication_id == medication.id,
            MedicationDoseLog.scheduled_for == target_date,
        )
        .all()
    )
    if existing:
        return existing

    expected_count = 2 if medication.frequency == "twice_daily" else 1
    if medication.frequency in {"weekly", "monthly", "as_needed"}:
        expected_count = 1

    created: list[MedicationDoseLog] = []
    for index in range(expected_count):
        created.append(
            MedicationDoseLog(
                user_id=user_id,
                family_member_id=family_member_id,
                medication_id=medication.id,
                scheduled_for=target_date,
                status="pending",
                notes=f"Auto-generated schedule slot {index + 1}",
            )
        )
    db.add_all(created)
    db.commit()
    return (
        db.query(MedicationDoseLog)
        .filter(
            MedicationDoseLog.user_id == user_id,
            MedicationDoseLog.medication_id == medication.id,
            MedicationDoseLog.scheduled_for == target_date,
        )
        .order_by(MedicationDoseLog.id.asc())
        .all()
    )


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def add_medication(
    payload: MedicationCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Add a new medication."""
    medication = Medication(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(medication)
    db.commit()
    db.refresh(medication)
    return MedicationResponse.model_validate(medication)


@router.get("", response_model=list[MedicationResponse])
async def list_medications(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[MedicationResponse]:
    """List medications with optional active filter."""
    query = _scoped_medication_query(
        db,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )

    if is_active is not None:
        query = query.filter(Medication.is_active == is_active)

    meds = query.order_by(Medication.created_at.desc()).offset(offset).limit(limit).all()
    return model_list(meds, MedicationResponse)


@router.post("/{medication_id}/doses", response_model=MedicationDoseLogResponse, status_code=status.HTTP_201_CREATED)
async def log_medication_dose(
    medication_id: int,
    payload: MedicationDoseLogCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationDoseLogResponse:
    medication = get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Medication not found.",
    )
    dose_log = (
        _scoped_dose_query(
            db,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            MedicationDoseLog.medication_id == medication.id,
            MedicationDoseLog.scheduled_for == payload.scheduled_for,
            MedicationDoseLog.scheduled_time == payload.scheduled_time,
        )
        .order_by(MedicationDoseLog.id.desc())
        .first()
    )

    if dose_log is None:
        dose_log = MedicationDoseLog(
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
            medication_id=medication.id,
            **payload.model_dump(),
        )
        db.add(dose_log)
    else:
        dose_log.status = payload.status
        dose_log.taken_at = payload.taken_at
        dose_log.notes = payload.notes

    db.commit()
    db.refresh(dose_log)
    return MedicationDoseLogResponse.model_validate(dose_log)


@router.get("/dashboard", response_model=MedicationDashboardResponse)
async def medication_dashboard(
    target_date: Optional[date] = Query(default=None),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationDashboardResponse:
    effective_date = target_date or date.today()
    medications = (
        _scoped_medication_query(
            db,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Medication.is_active.is_(True))
        .order_by(Medication.created_at.asc())
        .all()
    )

    items: list[MedicationDashboardItem] = []
    taken = 0
    missed = 0
    left = 0

    for medication in medications:
        logs = _ensure_today_dose_logs(
            db,
            medication=medication,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
            target_date=effective_date,
        )
        status_counts = defaultdict(int)
        for log in logs:
            status_counts[log.status] += 1

        taken += status_counts["taken"]
        missed += status_counts["missed"]
        left += status_counts["pending"]
        total = len(logs) if logs else 1
        adherence = round((status_counts["taken"] / total) * 100)
        latest_status = "pending"
        if status_counts["taken"]:
            latest_status = "taken"
        elif status_counts["missed"]:
            latest_status = "missed"

        items.append(
            MedicationDashboardItem(
                medication=MedicationResponse.model_validate(medication),
                adherence_pct=adherence,
                latest_status=latest_status,
                schedule_label=_schedule_label(medication),
            )
        )

    total_slots = max(taken + missed + left, 1)
    return MedicationDashboardResponse(
        taken=taken,
        missed=missed,
        left=left,
        adherence_pct=round((taken / total_slots) * 100) if total_slots else 0,
        items=items,
    )


@router.get("/adherence", response_model=MedicationAdherenceResponse)
async def medication_adherence(
    view: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    reference_date: Optional[date] = Query(default=None),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationAdherenceResponse:
    anchor = reference_date or date.today()
    medications = (
        _scoped_medication_query(
            db,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Medication.is_active.is_(True))
        .order_by(Medication.created_at.asc())
        .all()
    )
    if view == "daily":
        return MedicationAdherenceResponse(view="daily")

    if view == "weekly":
        weekday_start = anchor - timedelta(days=anchor.weekday())
        rows: list[MedicationWeeklyMatrixEntry] = []
        for medication in medications:
            day_statuses: list[str] = []
            for offset in range(7):
                day = weekday_start + timedelta(days=offset)
                logs = (
                    _scoped_dose_query(
                        db,
                        user_id=user.id,
                        family_member_id=profile_scope.family_member_id,
                    )
                    .filter(
                        MedicationDoseLog.medication_id == medication.id,
                        MedicationDoseLog.scheduled_for == day,
                    )
                    .all()
                )
                if not logs:
                    day_statuses.append("none")
                    continue
                if any(log.status == "missed" for log in logs):
                    day_statuses.append("missed")
                elif any(log.status == "taken" for log in logs):
                    day_statuses.append("taken")
                else:
                    day_statuses.append("pending")
            rows.append(
                MedicationWeeklyMatrixEntry(
                    medication_id=medication.id,
                    medication_name=medication.name,
                    dosage=medication.dosage,
                    day_statuses=day_statuses,
                )
            )
        return MedicationAdherenceResponse(view="weekly", weekly_rows=rows)

    month_start = anchor.replace(day=1)
    if anchor.month == 12:
        month_end = anchor.replace(year=anchor.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = anchor.replace(month=anchor.month + 1, day=1) - timedelta(days=1)

    monthly_days: list[MedicationMonthlyCalendarDay] = []
    current = month_start
    while current <= month_end:
        logs = (
            _scoped_dose_query(
                db,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(MedicationDoseLog.scheduled_for == current)
            .all()
        )
        if not logs:
            bucket = "none"
        else:
            taken_count = sum(1 for log in logs if log.status == "taken")
            adherence = taken_count / len(logs)
            if adherence >= 0.9:
                bucket = "high"
            elif adherence >= 0.7:
                bucket = "medium"
            else:
                bucket = "low"
        monthly_days.append(
            MedicationMonthlyCalendarDay(day=current.day, adherence_bucket=bucket)
        )
        current += timedelta(days=1)

    return MedicationAdherenceResponse(view="monthly", monthly_days=monthly_days)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Get a single medication by ID."""
    med = get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Medication not found.",
    )
    return MedicationResponse.model_validate(med)


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Update a medication (partial update)."""
    med = get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Medication not found.",
    )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(med, field, value)

    db.commit()
    db.refresh(med)
    return MedicationResponse.model_validate(med)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    """Delete a medication."""
    med = get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Medication not found.",
    )
    db.delete(med)
    db.commit()
