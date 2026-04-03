"""Chronic Symptoms endpoints — CRUD operations and quick-log summaries."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404, model_list
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.symptom import ChronicSymptom
from app.models.symptom_event import SymptomEvent
from app.models.user import User
from app.schemas.health import (
    SymptomCreate,
    SymptomDashboardItem,
    SymptomEventCreate,
    SymptomEventResponse,
    SymptomResponse,
    SymptomUpdate,
    SymptomWeeklyPattern,
)

router = APIRouter(prefix="/symptoms", tags=["Chronic Symptoms"])


def _severity_label(value: int) -> str:
    if value <= 3:
        return "mild"
    if value <= 6:
        return "moderate"
    return "severe"


def _trend_label(events: list[SymptomEvent]) -> str:
    today = datetime.now(timezone.utc).date()
    this_week_start = today - timedelta(days=6)
    prev_week_start = today - timedelta(days=13)
    this_week = sum(1 for item in events if item.occurred_at.date() >= this_week_start)
    prev_week = sum(
        1
        for item in events
        if prev_week_start <= item.occurred_at.date() < this_week_start
    )
    if prev_week == this_week:
        return "stable"
    return "improving" if this_week < prev_week else "worsening"


def _weekly_pattern(events: list[SymptomEvent]) -> list[SymptomWeeklyPattern]:
    counts = Counter(item.occurred_at.strftime("%a") for item in events)
    ordered = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [SymptomWeeklyPattern(weekday=day, count=counts.get(day, 0)) for day in ordered]


@router.post("", response_model=SymptomResponse, status_code=status.HTTP_201_CREATED)
async def add_symptom(
    payload: SymptomCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Add a new chronic symptom to track."""
    symptom = ChronicSymptom(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(symptom)
    db.commit()
    db.refresh(symptom)
    return SymptomResponse.model_validate(symptom)


@router.get("", response_model=list[SymptomResponse])
async def list_symptoms(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[SymptomResponse]:
    """List chronic symptoms with optional active filter."""
    query = apply_profile_scope(
        db.query(ChronicSymptom),
        ChronicSymptom,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )

    if is_active is not None:
        query = query.filter(ChronicSymptom.is_active == is_active)

    symptoms = query.order_by(ChronicSymptom.created_at.desc()).offset(offset).limit(limit).all()
    return model_list(symptoms, SymptomResponse)


@router.post("/quick-log", response_model=SymptomEventResponse, status_code=status.HTTP_201_CREATED)
async def quick_log_symptom(
    payload: SymptomEventCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> SymptomEventResponse:
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    event = SymptomEvent(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        symptom_name=payload.symptom_name,
        severity=payload.severity,
        notes=payload.notes,
        occurred_at=occurred_at,
    )
    db.add(event)

    chronic = (
        apply_profile_scope(
            db.query(ChronicSymptom),
            ChronicSymptom,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(ChronicSymptom.symptom_name == payload.symptom_name)
        .first()
    )
    if chronic is None:
        chronic = ChronicSymptom(
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
            symptom_name=payload.symptom_name,
            severity=payload.severity,
            frequency="intermittent",
            first_noticed=occurred_at.date(),
            is_active=True,
            notes=payload.notes,
        )
        db.add(chronic)
    else:
        chronic.severity = payload.severity
        chronic.is_active = True
        if payload.notes:
            chronic.notes = payload.notes

    db.commit()
    db.refresh(event)
    return SymptomEventResponse.model_validate(event)


@router.get("/dashboard", response_model=list[SymptomDashboardItem])
async def symptoms_dashboard(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[SymptomDashboardItem]:
    symptoms = (
        apply_profile_scope(
            db.query(ChronicSymptom),
            ChronicSymptom,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(ChronicSymptom.is_active.is_(True))
        .order_by(ChronicSymptom.updated_at.desc())
        .all()
    )
    response: list[SymptomDashboardItem] = []
    lookback_start = datetime.now(timezone.utc) - timedelta(days=13)
    for symptom in symptoms:
        events = (
            apply_profile_scope(
                db.query(SymptomEvent),
                SymptomEvent,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(
                SymptomEvent.symptom_name == symptom.symptom_name,
                SymptomEvent.occurred_at >= lookback_start,
            )
            .order_by(SymptomEvent.occurred_at.asc())
            .all()
        )
        count_this_week = sum(
            1
            for item in events
            if item.occurred_at.date() >= datetime.now(timezone.utc).date() - timedelta(days=6)
        )
        frequency_label = "Daily" if count_this_week >= 6 else f"{count_this_week}x this week"
        response.append(
            SymptomDashboardItem(
                symptom_name=symptom.symptom_name.replace("_", " ").title(),
                severity_label=_severity_label(symptom.severity),
                frequency_label=frequency_label,
                trend=_trend_label(events),  # type: ignore[arg-type]
                pattern=_weekly_pattern(events),
            )
        )
    return response


@router.get("/{symptom_id}", response_model=SymptomResponse)
async def get_symptom(
    symptom_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Get a single chronic symptom by ID."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Symptom not found.",
    )
    return SymptomResponse.model_validate(symptom)


@router.put("/{symptom_id}", response_model=SymptomResponse)
async def update_symptom(
    symptom_id: int,
    payload: SymptomUpdate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Update a chronic symptom (partial update)."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Symptom not found.",
    )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(symptom, field, value)

    db.commit()
    db.refresh(symptom)
    return SymptomResponse.model_validate(symptom)


@router.delete("/{symptom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symptom(
    symptom_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    """Delete a chronic symptom."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Symptom not found.",
    )
    db.delete(symptom)
    db.commit()
