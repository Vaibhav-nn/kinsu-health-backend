"""Reminders endpoints — CRUD operations and timeline view."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404, model_list
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.medication import Medication
from app.models.reminder import Reminder
from app.models.user import User
from app.schemas.health import ReminderCreate, ReminderResponse, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    """Create a new reminder."""
    if payload.linked_medication_id is not None:
        medication = (
            apply_profile_scope(
                db.query(Medication),
                Medication,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(Medication.id == payload.linked_medication_id)
            .first()
        )
        if medication is None:
            raise HTTPException(status_code=404, detail="Linked medication not found.")

    reminder = Reminder(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return ReminderResponse.model_validate(reminder)


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    reminder_type: Optional[str] = Query(None, description="Filter by type"),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    """List reminders with optional filters."""
    query = apply_profile_scope(
        db.query(Reminder),
        Reminder,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )

    if reminder_type:
        query = query.filter(Reminder.reminder_type == reminder_type)
    if is_enabled is not None:
        query = query.filter(Reminder.is_enabled == is_enabled)

    reminders = query.order_by(Reminder.scheduled_time.asc()).offset(offset).limit(limit).all()
    return model_list(reminders, ReminderResponse)


@router.get("/timeline", response_model=list[ReminderResponse])
async def reminder_timeline(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    """Get today's active reminders sorted by scheduled time (timeline view)."""
    reminders = apply_profile_scope(
        db.query(Reminder),
        Reminder,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    ).filter(
        Reminder.is_enabled.is_(True),
    ).order_by(Reminder.scheduled_time.asc()).all()
    return model_list(reminders, ReminderResponse)


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    """Get a single reminder by ID."""
    reminder = get_user_owned_or_404(
        db,
        Reminder,
        item_id=reminder_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Reminder not found.",
    )
    return ReminderResponse.model_validate(reminder)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    """Update a reminder (partial update)."""
    reminder = get_user_owned_or_404(
        db,
        Reminder,
        item_id=reminder_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Reminder not found.",
    )

    update_data = payload.model_dump(exclude_unset=True)
    if "linked_medication_id" in update_data and update_data["linked_medication_id"] is not None:
        medication = (
            apply_profile_scope(
                db.query(Medication),
                Medication,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(Medication.id == update_data["linked_medication_id"])
            .first()
        )
        if medication is None:
            raise HTTPException(status_code=404, detail="Linked medication not found.")

    for field, value in update_data.items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return ReminderResponse.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    """Delete a reminder."""
    reminder = get_user_owned_or_404(
        db,
        Reminder,
        item_id=reminder_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Reminder not found.",
    )
    db.delete(reminder)
    db.commit()
