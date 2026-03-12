"""Chronic Symptoms endpoints — CRUD operations."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import get_user_owned_or_404, model_list
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.symptom import ChronicSymptom
from app.models.user import User
from app.schemas.health import SymptomCreate, SymptomResponse, SymptomUpdate

router = APIRouter(prefix="/symptoms", tags=["Chronic Symptoms"])


@router.post("/", response_model=SymptomResponse, status_code=status.HTTP_201_CREATED)
async def add_symptom(
    payload: SymptomCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Add a new chronic symptom to track."""
    symptom = ChronicSymptom(user_id=user.id, **payload.model_dump())
    db.add(symptom)
    db.commit()
    db.refresh(symptom)
    return SymptomResponse.model_validate(symptom)


@router.get("/", response_model=list[SymptomResponse])
async def list_symptoms(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SymptomResponse]:
    """List chronic symptoms with optional active filter."""
    query = db.query(ChronicSymptom).filter(ChronicSymptom.user_id == user.id)

    if is_active is not None:
        query = query.filter(ChronicSymptom.is_active == is_active)

    symptoms = query.order_by(ChronicSymptom.created_at.desc()).offset(offset).limit(limit).all()
    return model_list(symptoms, SymptomResponse)


@router.get("/{symptom_id}", response_model=SymptomResponse)
async def get_symptom(
    symptom_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Get a single chronic symptom by ID."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
        not_found_detail="Symptom not found.",
    )
    return SymptomResponse.model_validate(symptom)


@router.put("/{symptom_id}", response_model=SymptomResponse)
async def update_symptom(
    symptom_id: int,
    payload: SymptomUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SymptomResponse:
    """Update a chronic symptom (partial update)."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
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
    db: Session = Depends(get_db),
) -> None:
    """Delete a chronic symptom."""
    symptom = get_user_owned_or_404(
        db,
        ChronicSymptom,
        item_id=symptom_id,
        user_id=user.id,
        not_found_detail="Symptom not found.",
    )
    db.delete(symptom)
    db.commit()
