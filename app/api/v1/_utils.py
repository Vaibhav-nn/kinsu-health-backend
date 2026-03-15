"""Shared helper utilities for v1 API routers."""

from typing import Any, Sequence, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def model_list(items: Sequence[Any], schema: type[SchemaT]) -> list[SchemaT]:
    """Serialize ORM rows into a typed response schema list."""
    return [schema.model_validate(item) for item in items]


async def get_user_owned_or_404(
    db: AsyncSession,
    model: Any,
    *,
    item_id: int,
    user_id: int,
    not_found_detail: str,
) -> Any:
    """Fetch a user-owned row by id or raise a 404."""
    result = await db.execute(
        select(model).where(model.id == item_id, model.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        logger.warning(
            "Resource not found",
            extra={
                "extra_fields": {
                    "model": model.__name__,
                    "item_id": item_id,
                    "user_id": user_id,
                }
            },
        )
        raise HTTPException(status_code=404, detail=not_found_detail)
    return item
