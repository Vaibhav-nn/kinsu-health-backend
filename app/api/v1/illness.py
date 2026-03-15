"""Illness Episodes endpoints — CRUD with detailed view and sub-resource details."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.illness import IllnessDetail, IllnessEpisode
from app.models.user import User
from app.schemas.health import (
    IllnessDetailCreate,
    IllnessDetailResponse,
    IllnessEpisodeCreate,
    IllnessEpisodeDetailedResponse,
    IllnessEpisodeResponse,
    IllnessEpisodeUpdate,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/illness", tags=["Illness Episodes"])


@router.post("/", response_model=IllnessEpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    payload: IllnessEpisodeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IllnessEpisodeResponse:
    """Create a new illness episode."""
    logger.info(
        "Creating illness episode",
        extra={"extra_fields": {"user_id": str(user.id), "name": payload.name}},
    )
    
    episode = IllnessEpisode(user_id=user.id, **payload.model_dump())
    db.add(episode)
    await db.flush()
    await db.refresh(episode)
    
    logger.debug("Illness episode created", extra={"extra_fields": {"episode_id": episode.id}})
    
    return IllnessEpisodeResponse.model_validate(episode)


@router.get("/", response_model=list[IllnessEpisodeResponse])
async def list_episodes(
    episode_status: Optional[str] = Query(
        None, alias="status", description="Filter by status: active, recovered, chronic"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IllnessEpisodeResponse]:
    """List illness episodes with optional status filter."""
    logger.debug(
        "Listing illness episodes",
        extra={"extra_fields": {"user_id": str(user.id), "status": episode_status}},
    )
    
    query = select(IllnessEpisode).where(IllnessEpisode.user_id == user.id)

    if episode_status:
        query = query.where(IllnessEpisode.status == episode_status)

    result = await db.execute(
        query.order_by(IllnessEpisode.start_date.desc()).offset(offset).limit(limit)
    )
    episodes = result.scalars().all()
    
    logger.info("Illness episodes retrieved", extra={"extra_fields": {"count": len(episodes)}})
    
    return [IllnessEpisodeResponse.model_validate(e) for e in episodes]


@router.get("/{episode_id}", response_model=IllnessEpisodeDetailedResponse)
async def get_episode_detailed(
    episode_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IllnessEpisodeDetailedResponse:
    """Get a single illness episode with all detail entries (detailed view)."""
    result = await db.execute(
        select(IllnessEpisode)
        .options(joinedload(IllnessEpisode.details))
        .where(
            IllnessEpisode.id == episode_id,
            IllnessEpisode.user_id == user.id,
        )
    )
    episode = result.scalar_one_or_none()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    return IllnessEpisodeDetailedResponse.model_validate(episode)


@router.put("/{episode_id}", response_model=IllnessEpisodeResponse)
async def update_episode(
    episode_id: int,
    payload: IllnessEpisodeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IllnessEpisodeResponse:
    """Update an illness episode (partial update)."""
    result = await db.execute(
        select(IllnessEpisode).where(
            IllnessEpisode.id == episode_id,
            IllnessEpisode.user_id == user.id,
        )
    )
    episode = result.scalar_one_or_none()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(episode, field, value)

    await db.flush()
    await db.refresh(episode)
    return IllnessEpisodeResponse.model_validate(episode)


@router.post(
    "/{episode_id}/details",
    response_model=IllnessDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_episode_detail(
    episode_id: int,
    payload: IllnessDetailCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IllnessDetailResponse:
    """Add a detail entry (symptom, diagnosis, treatment, note) to an episode."""
    logger.info(
        "Adding detail to illness episode",
        extra={"extra_fields": {"episode_id": episode_id, "detail_type": payload.detail_type}},
    )
    
    # Verify the episode belongs to the user
    result = await db.execute(
        select(IllnessEpisode).where(
            IllnessEpisode.id == episode_id,
            IllnessEpisode.user_id == user.id,
        )
    )
    episode = result.scalar_one_or_none()

    if not episode:
        logger.warning("Illness episode not found", extra={"extra_fields": {"episode_id": episode_id}})
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    detail_data = payload.model_dump()
    if detail_data.get("recorded_at") is None:
        detail_data["recorded_at"] = datetime.now(timezone.utc)

    detail = IllnessDetail(episode_id=episode_id, **detail_data)
    db.add(detail)
    await db.flush()
    await db.refresh(detail)
    
    logger.debug("Illness detail added successfully", extra={"extra_fields": {"detail_id": detail.id}})
    
    return IllnessDetailResponse.model_validate(detail)


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an illness episode and all its details (cascade)."""
    result = await db.execute(
        select(IllnessEpisode).where(
            IllnessEpisode.id == episode_id,
            IllnessEpisode.user_id == user.id,
        )
    )
    episode = result.scalar_one_or_none()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    await db.delete(episode)
    await db.flush()
