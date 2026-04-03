"""Family member APIs for linked profiles and account switching."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.caregiver_permission import CaregiverPermission
from app.models.family import FamilyMember
from app.models.medication import Medication
from app.models.medication_dose_log import MedicationDoseLog
from app.models.user import User
from app.models.vault import HealthRecord
from app.models.vital import VitalLog
from app.schemas.family import (
    AccountProfileOption,
    CaregiverPermissionResponse,
    CaregiverPermissionUpdate,
    FamilyDashboardCard,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyMemberUpdate,
)

router = APIRouter(prefix="/family", tags=["Family"])

_PERMISSION_CATALOG: dict[str, tuple[str, str]] = {
    "view_records": ("View health records", "Access uploaded documents and reports"),
    "log_vitals": ("Log vitals", "Record blood pressure, sugar, and other vitals"),
    "manage_medications": ("Manage medications", "Add or update medication schedules"),
    "log_symptoms": ("Log symptoms", "Record symptoms on behalf of patient"),
    "receive_sos": ("Receive SOS alerts", "Get notified during emergency triggers"),
    "view_ai_summaries": ("View AI summaries", "Access AI-generated health insights"),
}


def _get_member_or_404(db: Session, user_id: int, member_id: int) -> FamilyMember:
    member = (
        db.query(FamilyMember)
        .filter(FamilyMember.id == member_id, FamilyMember.owner_user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Family member not found.")
    return member


def _compute_age(dob: date | None) -> int | None:
    if dob is None:
        return None
    today = date.today()
    return today.year - dob.year - (1 if (today.month, today.day) < (dob.month, dob.day) else 0)


def _relative_day_label(day_value: date) -> str:
    today = date.today()
    if day_value == today:
        return "today"
    if day_value == today - timedelta(days=1):
        return "yesterday"
    return day_value.strftime("%d %b").lstrip("0")


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    if not parts:
        return "U"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _member_last_activity(db: Session, user_id: int, family_member_id: int | None) -> str:
    latest_vital = (
        db.query(VitalLog)
        .filter(
            VitalLog.user_id == user_id,
            VitalLog.family_member_id.is_(None) if family_member_id is None else VitalLog.family_member_id == family_member_id,
        )
        .order_by(VitalLog.recorded_at.desc())
        .first()
    )
    latest_dose = (
        db.query(MedicationDoseLog)
        .filter(
            MedicationDoseLog.user_id == user_id,
            MedicationDoseLog.family_member_id.is_(None)
            if family_member_id is None
            else MedicationDoseLog.family_member_id == family_member_id,
        )
        .order_by(MedicationDoseLog.updated_at.desc())
        .first()
    )

    candidates: list[tuple[str, date]] = []
    if latest_vital:
        label = latest_vital.vital_type.replace("_", " ").title()
        activity_day = latest_vital.recorded_at.date()
        candidates.append((f"{label} logged {_relative_day_label(activity_day)}", activity_day))
    if latest_dose:
        label = "Medication taken" if latest_dose.status == "taken" else "Medication updated"
        activity_date = (latest_dose.taken_at or latest_dose.updated_at).date()
        candidates.append((f"{label} {_relative_day_label(activity_date)}", activity_date))

    if not candidates:
        return "Profile created"
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def _dashboard_card(
    *,
    db: Session,
    user: User,
    profile_type: str,
    profile_id: int | None,
    display_name: str,
    relation: str,
    date_of_birth: date | None,
    blood_group: str | None,
    conditions: list[str] | None,
    is_active_context: bool,
) -> FamilyDashboardCard:
    records_query = db.query(HealthRecord).filter(HealthRecord.user_id == user.id)
    meds_query = db.query(Medication).filter(Medication.user_id == user.id, Medication.is_active.is_(True))
    if profile_id is None:
        records_query = records_query.filter(HealthRecord.family_member_id.is_(None))
        meds_query = meds_query.filter(Medication.family_member_id.is_(None))
    else:
        records_query = records_query.filter(HealthRecord.family_member_id == profile_id)
        meds_query = meds_query.filter(Medication.family_member_id == profile_id)

    return FamilyDashboardCard(
        profile_type=profile_type,  # type: ignore[arg-type]
        profile_id=profile_id,
        display_name=display_name,
        relation=relation,
        age=_compute_age(date_of_birth),
        blood_group=blood_group,
        initials=_initials(display_name),
        health_conditions=list(conditions or []),
        record_count=records_query.count(),
        medication_count=meds_query.count(),
        last_activity=_member_last_activity(db, user.id, profile_id),
        is_active_context=is_active_context,
    )


def _permission_response(permission: CaregiverPermission) -> CaregiverPermissionResponse:
    label, description = _PERMISSION_CATALOG.get(
        permission.permission_key,
        (permission.permission_key.replace("_", " ").title(), ""),
    )
    return CaregiverPermissionResponse(
        permission_key=permission.permission_key,
        label=label,
        description=description,
        is_enabled=permission.is_enabled,
    )


def _get_or_create_permissions(
    db: Session,
    *,
    user_id: int,
    family_member_id: int,
) -> list[CaregiverPermission]:
    permissions = (
        db.query(CaregiverPermission)
        .filter(
            CaregiverPermission.owner_user_id == user_id,
            CaregiverPermission.family_member_id == family_member_id,
        )
        .order_by(CaregiverPermission.permission_key.asc())
        .all()
    )
    if permissions:
        return permissions

    permissions = [
        CaregiverPermission(
            owner_user_id=user_id,
            family_member_id=family_member_id,
            permission_key=key,
            is_enabled=(key != "view_ai_summaries"),
        )
        for key in _PERMISSION_CATALOG
    ]
    db.add_all(permissions)
    db.commit()
    return (
        db.query(CaregiverPermission)
        .filter(
            CaregiverPermission.owner_user_id == user_id,
            CaregiverPermission.family_member_id == family_member_id,
        )
        .order_by(CaregiverPermission.permission_key.asc())
        .all()
    )


@router.post("/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: FamilyMemberCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FamilyMemberResponse:
    """Create a new linked family member profile."""
    member = FamilyMember(owner_user_id=user.id, **payload.model_dump())
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A family member with this phone number already exists.",
        ) from exc
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


@router.get("/members", response_model=list[FamilyMemberResponse])
async def list_members(
    include_inactive: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FamilyMemberResponse]:
    """List linked family members for the current owner account."""
    query = db.query(FamilyMember).filter(FamilyMember.owner_user_id == user.id)
    if not include_inactive:
        query = query.filter(FamilyMember.is_active.is_(True))
    members = query.order_by(FamilyMember.created_at.desc()).all()
    return [FamilyMemberResponse.model_validate(item) for item in members]


@router.get("/members/{member_id}", response_model=FamilyMemberResponse)
async def get_member(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FamilyMemberResponse:
    member = _get_member_or_404(db, user.id, member_id)
    return FamilyMemberResponse.model_validate(member)


@router.put("/members/{member_id}", response_model=FamilyMemberResponse)
async def update_member(
    member_id: int,
    payload: FamilyMemberUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FamilyMemberResponse:
    """Update a linked family member profile."""
    member = _get_member_or_404(db, user.id, member_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A family member with this phone number already exists.",
        ) from exc
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_member(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete (deactivate) a linked family member profile."""
    member = _get_member_or_404(db, user.id, member_id)
    if member.is_active:
        member.is_active = False
        db.commit()


@router.get("/profiles", response_model=list[AccountProfileOption])
async def list_profiles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AccountProfileOption]:
    """Return switchable profiles for account-switcher UI."""
    options: list[AccountProfileOption] = [
        AccountProfileOption(
            profile_type="self",
            profile_id=None,
            display_name=user.display_name or user.email.split("@")[0],
            subtitle=user.email,
        )
    ]
    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.owner_user_id == user.id, FamilyMember.is_active.is_(True))
        .order_by(FamilyMember.display_name.asc())
        .all()
    )
    for member in members:
        subtitle = " · ".join(
            part
            for part in [member.relation or "", member.phone_e164]
            if part
        )
        options.append(
            AccountProfileOption(
                profile_type="family_member",
                profile_id=member.id,
                display_name=member.display_name,
                subtitle=subtitle or None,
            )
        )
    return options


@router.get("/dashboard", response_model=list[FamilyDashboardCard])
async def family_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FamilyDashboardCard]:
    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.owner_user_id == user.id, FamilyMember.is_active.is_(True))
        .order_by(FamilyMember.created_at.asc())
        .all()
    )

    cards = [
        _dashboard_card(
            db=db,
            user=user,
            profile_type="self",
            profile_id=None,
            display_name=user.display_name or user.email.split("@")[0],
            relation="Self",
            date_of_birth=user.date_of_birth,
            blood_group=user.blood_group,
            conditions=user.health_goals or [],
            is_active_context=True,
        )
    ]
    for member in members:
        cards.append(
            _dashboard_card(
                db=db,
                user=user,
                profile_type="family_member",
                profile_id=member.id,
                display_name=member.display_name,
                relation=member.relation or "Family",
                date_of_birth=member.date_of_birth,
                blood_group=member.blood_group,
                conditions=member.health_conditions or [],
                is_active_context=False,
            )
        )
    return cards


@router.get("/members/{member_id}/permissions", response_model=list[CaregiverPermissionResponse])
async def list_permissions(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CaregiverPermissionResponse]:
    _get_member_or_404(db, user.id, member_id)
    permissions = _get_or_create_permissions(db, user_id=user.id, family_member_id=member_id)
    return [_permission_response(item) for item in permissions]


@router.put("/members/{member_id}/permissions", response_model=list[CaregiverPermissionResponse])
async def update_permissions(
    member_id: int,
    payload: list[CaregiverPermissionUpdate],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CaregiverPermissionResponse]:
    _get_member_or_404(db, user.id, member_id)
    permissions = {
        item.permission_key: item
        for item in _get_or_create_permissions(db, user_id=user.id, family_member_id=member_id)
    }
    for item in payload:
        if item.permission_key not in permissions:
            continue
        permissions[item.permission_key].is_enabled = item.is_enabled
    db.commit()
    updated = (
        db.query(CaregiverPermission)
        .filter(
            CaregiverPermission.owner_user_id == user.id,
            CaregiverPermission.family_member_id == member_id,
        )
        .order_by(CaregiverPermission.permission_key.asc())
        .all()
    )
    return [_permission_response(item) for item in updated]
