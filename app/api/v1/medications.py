"""Medications endpoints — CRUD operations."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1._utils import get_user_owned_or_404, model_list
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.medication import Medication
from app.models.user import User
from app.schemas.health import MedicationCreate, MedicationResponse, MedicationUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.post("/", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def add_medication(
    payload: MedicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    """Add a new medication."""
    logger.info(
        "Adding new medication",
        extra={"extra_fields": {"user_id": str(user.id), "name": payload.name}},
    )
    
    medication = Medication(user_id=user.id, **payload.model_dump())
    db.add(medication)
    await db.flush()
    await db.refresh(medication)
    
    logger.debug("Medication added successfully", extra={"extra_fields": {"medication_id": medication.id}})
    
    return MedicationResponse.model_validate(medication)


@router.get("/", response_model=list[MedicationResponse])
async def list_medications(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationResponse]:
    """List medications with optional active filter."""
    query = select(Medication).where(Medication.user_id == user.id)

    if is_active is not None:
        query = query.where(Medication.is_active == is_active)

    result = await db.execute(
        query.order_by(Medication.created_at.desc()).offset(offset).limit(limit)
    )
    meds = result.scalars().all()
    return model_list(meds, MedicationResponse)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    """Get a single medication by ID."""
    med = await get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        not_found_detail="Medication not found.",
    )
    return MedicationResponse.model_validate(med)


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    """Update a medication (partial update)."""
    med = await get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        not_found_detail="Medication not found.",
    )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(med, field, value)

    await db.flush()
    await db.refresh(med)
    return MedicationResponse.model_validate(med)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a medication."""
    logger.info("Deleting medication", extra={"extra_fields": {"medication_id": medication_id}})
    
    med = await get_user_owned_or_404(
        db,
        Medication,
        item_id=medication_id,
        user_id=user.id,
        not_found_detail="Medication not found.",
    )
    await db.delete(med)
    await db.flush()
    
    logger.info("Medication deleted successfully", extra={"extra_fields": {"medication_id": medication_id}})