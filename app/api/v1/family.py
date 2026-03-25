"""Family member APIs for linked profiles and account switching."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.family import FamilyMember
from app.models.user import User
from app.schemas.family import (
    AccountProfileOption,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyMemberUpdate,
)

router = APIRouter(prefix="/family", tags=["Family"])


def _get_member_or_404(db: Session, user_id: int, member_id: int) -> FamilyMember:
    member = (
        db.query(FamilyMember)
        .filter(FamilyMember.id == member_id, FamilyMember.owner_user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Family member not found.")
    return member


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
