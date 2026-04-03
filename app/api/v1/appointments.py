"""Appointment APIs for home dashboard and scheduling flows."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.homescreen import AppointmentCreate, AppointmentUpdate, HomeAppointmentCard

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=HomeAppointmentCard, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeAppointmentCard:
    appointment = Appointment(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return HomeAppointmentCard.model_validate(appointment)


@router.get("", response_model=list[HomeAppointmentCard])
async def list_appointments(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    upcoming_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[HomeAppointmentCard]:
    query = apply_profile_scope(
        db.query(Appointment),
        Appointment,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    if upcoming_only:
        query = query.filter(Appointment.appointment_at >= datetime.now(timezone.utc))

    appointments = (
        query.order_by(Appointment.appointment_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [HomeAppointmentCard.model_validate(item) for item in appointments]


@router.get("/{appointment_id}", response_model=HomeAppointmentCard)
async def get_appointment(
    appointment_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeAppointmentCard:
    appointment = get_user_owned_or_404(
        db,
        Appointment,
        item_id=appointment_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Appointment not found.",
    )
    return HomeAppointmentCard.model_validate(appointment)


@router.put("/{appointment_id}", response_model=HomeAppointmentCard)
async def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeAppointmentCard:
    appointment = get_user_owned_or_404(
        db,
        Appointment,
        item_id=appointment_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Appointment not found.",
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    db.commit()
    db.refresh(appointment)
    return HomeAppointmentCard.model_validate(appointment)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    appointment = get_user_owned_or_404(
        db,
        Appointment,
        item_id=appointment_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Appointment not found.",
    )
    db.delete(appointment)
    db.commit()
