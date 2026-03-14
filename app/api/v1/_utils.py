"""Shared helper utilities for v1 API routers."""

from typing import Any, Sequence, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def model_list(items: Sequence[Any], schema: type[SchemaT]) -> list[SchemaT]:
    """Serialize ORM rows into a typed response schema list."""
    return [schema.model_validate(item) for item in items]


def get_user_owned_or_404(
    db: Session,
    model: Any,
    *,
    item_id: int,
    user_id: int,
    not_found_detail: str,
) -> Any:
    """Fetch a user-owned row by id or raise a 404."""
    item = db.query(model).filter(model.id == item_id, model.user_id == user_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return item
