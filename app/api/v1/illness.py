"""Illness Episodes endpoints — CRUD with detailed view and sub-resource details."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1._utils import apply_profile_scope
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.illness import IllnessDetail, IllnessEpisode
from app.models.user import User
from app.schemas.health import (
    IllnessDashboardCard,
    IllnessDetailCreate,
    IllnessDetailResponse,
    IllnessEpisodeCreate,
    IllnessEpisodeDetailedResponse,
    IllnessEpisodeResponse,
    IllnessEpisodeUpdate,
)

router = APIRouter(prefix="/illness", tags=["Illness Episodes"])


@router.post("", response_model=IllnessEpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    payload: IllnessEpisodeCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> IllnessEpisodeResponse:
    """Create a new illness episode."""
    episode = IllnessEpisode(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        **payload.model_dump(),
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return IllnessEpisodeResponse.model_validate(episode)


@router.get("", response_model=list[IllnessEpisodeResponse])
async def list_episodes(
    episode_status: Optional[str] = Query(
        None, alias="status", description="Filter by status: active, recovered, chronic"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[IllnessEpisodeResponse]:
    """List illness episodes with optional status filter."""
    query = db.query(IllnessEpisode).filter(IllnessEpisode.user_id == user.id)
    if profile_scope.family_member_id is None:
        query = query.filter(IllnessEpisode.family_member_id.is_(None))
    else:
        query = query.filter(IllnessEpisode.family_member_id == profile_scope.family_member_id)

    if episode_status:
        query = query.filter(IllnessEpisode.status == episode_status)

    episodes = query.order_by(IllnessEpisode.start_date.desc()).offset(offset).limit(limit).all()
    return [IllnessEpisodeResponse.model_validate(e) for e in episodes]


@router.get("/dashboard", response_model=list[IllnessDashboardCard])
async def illness_dashboard(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[IllnessDashboardCard]:
    episodes = (
        apply_profile_scope(
            db.query(IllnessEpisode).options(joinedload(IllnessEpisode.details)),
            IllnessEpisode,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .order_by(IllnessEpisode.updated_at.desc())
        .all()
    )
    cards: list[IllnessDashboardCard] = []
    for episode in episodes:
        detail_items = list(episode.details or [])
        tags = [
            item.content
            for item in detail_items
            if item.detail_type in {"symptom", "diagnosis"}
        ][:3]
        if episode.end_date:
            subtitle = f"{episode.start_date.strftime('%-d %b %Y')} - {episode.end_date.strftime('%-d %b %Y')}"
        else:
            subtitle = f"Ongoing since {episode.start_date.strftime('%b %Y')}"
        cards.append(
            IllnessDashboardCard(
                id=episode.id,
                title=episode.title,
                subtitle=subtitle,
                status=episode.status,
                tags=tags,
                consult_count=sum(1 for item in detail_items if item.detail_type == "consult"),
                report_count=sum(1 for item in detail_items if item.detail_type == "report"),
            )
        )
    return cards


@router.get("/{episode_id}", response_model=IllnessEpisodeDetailedResponse)
async def get_episode_detailed(
    episode_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> IllnessEpisodeDetailedResponse:
    """Get a single illness episode with all detail entries (detailed view)."""
    episode = (
        db.query(IllnessEpisode)
        .options(joinedload(IllnessEpisode.details))
        .filter(
            IllnessEpisode.id == episode_id,
            IllnessEpisode.user_id == user.id,
        )
    )
    if profile_scope.family_member_id is None:
        episode = episode.filter(IllnessEpisode.family_member_id.is_(None)).first()
    else:
        episode = episode.filter(
            IllnessEpisode.family_member_id == profile_scope.family_member_id
        ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    return IllnessEpisodeDetailedResponse.model_validate(episode)


@router.put("/{episode_id}", response_model=IllnessEpisodeResponse)
async def update_episode(
    episode_id: int,
    payload: IllnessEpisodeUpdate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> IllnessEpisodeResponse:
    """Update an illness episode (partial update)."""
    episode_query = db.query(IllnessEpisode).filter(
        IllnessEpisode.id == episode_id,
        IllnessEpisode.user_id == user.id,
    )
    if profile_scope.family_member_id is None:
        episode = episode_query.filter(IllnessEpisode.family_member_id.is_(None)).first()
    else:
        episode = episode_query.filter(
            IllnessEpisode.family_member_id == profile_scope.family_member_id
        ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(episode, field, value)

    db.commit()
    db.refresh(episode)
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
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> IllnessDetailResponse:
    """Add a detail entry (symptom, diagnosis, treatment, note) to an episode."""
    # Verify the episode belongs to the user
    episode_query = db.query(IllnessEpisode).filter(
        IllnessEpisode.id == episode_id,
        IllnessEpisode.user_id == user.id,
    )
    if profile_scope.family_member_id is None:
        episode = episode_query.filter(IllnessEpisode.family_member_id.is_(None)).first()
    else:
        episode = episode_query.filter(
            IllnessEpisode.family_member_id == profile_scope.family_member_id
        ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    detail_data = payload.model_dump()
    if detail_data.get("recorded_at") is None:
        detail_data["recorded_at"] = datetime.now(timezone.utc)

    detail = IllnessDetail(episode_id=episode_id, **detail_data)
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return IllnessDetailResponse.model_validate(detail)


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    """Delete an illness episode and all its details (cascade)."""
    episode_query = db.query(IllnessEpisode).filter(
        IllnessEpisode.id == episode_id,
        IllnessEpisode.user_id == user.id,
    )
    if profile_scope.family_member_id is None:
        episode = episode_query.filter(IllnessEpisode.family_member_id.is_(None)).first()
    else:
        episode = episode_query.filter(
            IllnessEpisode.family_member_id == profile_scope.family_member_id
        ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Illness episode not found.")

    db.delete(episode)
    db.commit()
