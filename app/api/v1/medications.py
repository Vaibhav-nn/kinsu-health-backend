"""Medications endpoints — CRUD operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.medication import Medication
from app.models.user import User
from app.schemas.health import MedicationCreate, MedicationResponse, MedicationUpdate

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.post("/", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def add_medication(
    payload: MedicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Add a new medication."""
    medication = Medication(user_id=user.id, **payload.model_dump())
    db.add(medication)
    db.commit()
    db.refresh(medication)
    return MedicationResponse.model_validate(medication)


@router.get("/", response_model=list[MedicationResponse])
async def list_medications(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MedicationResponse]:
    """List medications with optional active filter."""
    query = db.query(Medication).filter(Medication.user_id == user.id)

    if is_active is not None:
        query = query.filter(Medication.is_active == is_active)

    meds = query.order_by(Medication.created_at.desc()).offset(offset).limit(limit).all()
    return [MedicationResponse.model_validate(m) for m in meds]


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Get a single medication by ID."""
    med = db.query(Medication).filter(
        Medication.id == medication_id,
        Medication.user_id == user.id,
    ).first()

    if not med:
        raise HTTPException(status_code=404, detail="Medication not found.")

    return MedicationResponse.model_validate(med)


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicationResponse:
    """Update a medication (partial update)."""
    med = db.query(Medication).filter(
        Medication.id == medication_id,
        Medication.user_id == user.id,
    ).first()

    if not med:
        raise HTTPException(status_code=404, detail="Medication not found.")

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
    db: Session = Depends(get_db),
) -> None:
    """Delete a medication."""
    med = db.query(Medication).filter(
        Medication.id == medication_id,
        Medication.user_id == user.id,
    ).first()

    if not med:
        raise HTTPException(status_code=404, detail="Medication not found.")

    db.delete(med)
    db.commit()
