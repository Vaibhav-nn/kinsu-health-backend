"""Homescreen endpoints — overview, search, notifications, and preferences."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.home import HomeNotification, HomePreference
from app.models.medication import Medication
from app.models.symptom import ChronicSymptom
from app.models.user import User
from app.models.vital import VitalLog
from app.schemas.homescreen import (
    HomeAnimationConfig,
    HomeBottomNavItem,
    HomeNotificationCreate,
    HomeNotificationResponse,
    HomeOverviewResponse,
    HomePreferenceResponse,
    HomeQuickCard,
    HomeSearchResponse,
    HomeSearchResultItem,
    HomeThemeUpdate,
    HomeTopBarData,
    HomeTopBarProfile,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/homescreen", tags=["Homescreen"])


def _normalize_theme_mode(value: str) -> str:
    return value if value in {"light", "dark", "system"} else "system"


async def _get_or_create_preference(db: AsyncSession, user_id: int) -> HomePreference:
    result = await db.execute(select(HomePreference).where(HomePreference.user_id == user_id))
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = HomePreference(user_id=user_id, theme_mode="system")
        db.add(pref)
        await db.flush()
        await db.refresh(pref)
    return pref


def _resolve_profile(user: User) -> HomeTopBarProfile:
    display_name = user.display_name or user.email.split("@")[0]
    name_parts = [p for p in display_name.replace("_", " ").split(" ") if p]
    if not name_parts:
        initials = "U"
    elif len(name_parts) == 1:
        initials = name_parts[0][0].upper()
    else:
        initials = (name_parts[0][0] + name_parts[1][0]).upper()

    return HomeTopBarProfile(
        display_name=display_name,
        email=user.email,
        initials=initials,
    )


def _resolve_animation(active_symptoms: int, active_medications: int) -> HomeAnimationConfig:
    if active_symptoms > 0:
        return HomeAnimationConfig(
            animation_key="pulse_alert",
            headline="Keep symptoms in check",
            subheadline=f"{active_symptoms} active symptom(s) currently tracked.",
        )
    if active_medications > 0:
        return HomeAnimationConfig(
            animation_key="medication_wave",
            headline="Medication routine on track",
            subheadline=f"{active_medications} active medication(s) in your plan.",
        )
    return HomeAnimationConfig(
        animation_key="wellness_orb",
        headline="Welcome to your health home",
        subheadline="Track vitals, symptoms, and medications from one place.",
    )


@router.get("/overview", response_model=HomeOverviewResponse)
async def homescreen_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeOverviewResponse:
    """Get homescreen payload for top bar, animation, quick cards, and nav."""
    logger.debug("Fetching homescreen overview", extra={"extra_fields": {"user_id": str(user.id)}})
    
    pref = await _get_or_create_preference(db, user.id)
    
    unread_result = await db.execute(
        select(func.count())
        .select_from(HomeNotification)
        .where(HomeNotification.user_id == user.id, HomeNotification.is_read.is_(False))
    )
    unread_count = unread_result.scalar()

    latest_vital_result = await db.execute(
        select(VitalLog)
        .where(VitalLog.user_id == user.id)
        .order_by(VitalLog.recorded_at.desc())
        .limit(1)
    )
    latest_vital = latest_vital_result.scalar_one_or_none()
    
    active_symptoms_result = await db.execute(
        select(func.count())
        .select_from(ChronicSymptom)
        .where(ChronicSymptom.user_id == user.id, ChronicSymptom.is_active.is_(True))
    )
    active_symptoms = active_symptoms_result.scalar()
    
    active_medications_result = await db.execute(
        select(func.count())
        .select_from(Medication)
        .where(Medication.user_id == user.id, Medication.is_active.is_(True))
    )
    active_medications = active_medications_result.scalar()

    vital_value = "No vitals yet"
    vital_subtitle = "Add your first vital log"
    if latest_vital:
        vital_value = f"{latest_vital.value:g} {latest_vital.unit}"
        vital_subtitle = f"Latest: {latest_vital.vital_type.replace('_', ' ').title()}"

    cards = [
        HomeQuickCard(
            key="vitals",
            title="Vitals",
            value=vital_value,
            subtitle=vital_subtitle,
            route="/tracking/vitals",
        ),
        HomeQuickCard(
            key="symptoms",
            title="Symptoms",
            value=str(active_symptoms),
            subtitle="Active symptoms",
            route="/tracking/symptoms",
        ),
        HomeQuickCard(
            key="medications",
            title="Medications",
            value=str(active_medications),
            subtitle="Active medications",
            route="/tracking/medications",
        ),
    ]

    bottom_nav = [
        HomeBottomNavItem(key="home", label="Home", route="/home", is_active=True),
        HomeBottomNavItem(key="vault", label="Vault", route="/vault"),
        HomeBottomNavItem(key="tracking", label="Tracking", route="/tracking"),
        HomeBottomNavItem(key="family", label="Family", route="/family"),
        HomeBottomNavItem(key="ai", label="AI", route="/ai"),
    ]

    return HomeOverviewResponse(
        top_bar=HomeTopBarData(
            search_placeholder="Search health records, meds, symptoms...",
            notification_unread_count=unread_count,
            theme_mode=_normalize_theme_mode(pref.theme_mode),
            profile=_resolve_profile(user),
        ),
        top_half_animation=_resolve_animation(active_symptoms, active_medications),
        cards=cards,
        bottom_nav=bottom_nav,
    )


@router.get("/search", response_model=HomeSearchResponse)
async def homescreen_search(
    q: str = Query(..., min_length=1, max_length=120, description="Search query"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeSearchResponse:
    """Search across vitals, symptoms, and medications for homescreen results."""
    logger.info("Homescreen search initiated", extra={"extra_fields": {"query": q, "user_id": str(user.id)}})
    
    term = q.strip()
    if not term:
        return HomeSearchResponse(query=q, total=0, results=[])

    pattern = f"%{term}%"
    results: list[HomeSearchResultItem] = []

    vitals_result = await db.execute(
        select(VitalLog)
        .where(
            VitalLog.user_id == user.id,
            or_(
                VitalLog.vital_type.ilike(pattern),
                VitalLog.notes.ilike(pattern),
                VitalLog.unit.ilike(pattern),
            ),
        )
        .order_by(VitalLog.recorded_at.desc())
        .limit(10)
    )
    vitals = vitals_result.scalars().all()

    for item in vitals:
        results.append(
            HomeSearchResultItem(
                section="vitals",
                item_id=item.id,
                title=item.vital_type.replace("_", " ").title(),
                subtitle=f"{item.value:g} {item.unit}",
                route=f"/tracking/vitals/{item.id}",
            )
        )

    symptoms_result = await db.execute(
        select(ChronicSymptom)
        .where(
            ChronicSymptom.user_id == user.id,
            or_(
                ChronicSymptom.symptom_name.ilike(pattern),
                ChronicSymptom.body_area.ilike(pattern),
                ChronicSymptom.triggers.ilike(pattern),
                ChronicSymptom.notes.ilike(pattern),
            ),
        )
        .order_by(ChronicSymptom.updated_at.desc())
        .limit(10)
    )
    symptoms = symptoms_result.scalars().all()

    for item in symptoms:
        results.append(
            HomeSearchResultItem(
                section="symptoms",
                item_id=item.id,
                title=item.symptom_name.replace("_", " ").title(),
                subtitle=f"Severity {item.severity}/10",
                route=f"/tracking/symptoms/{item.id}",
            )
        )

    medications_result = await db.execute(
        select(Medication)
        .where(
            Medication.user_id == user.id,
            or_(
                Medication.name.ilike(pattern),
                Medication.dosage.ilike(pattern),
                Medication.prescribing_doctor.ilike(pattern),
                Medication.notes.ilike(pattern),
            ),
        )
        .order_by(Medication.updated_at.desc())
        .limit(10)
    )
    medications = medications_result.scalars().all()

    for item in medications:
        results.append(
            HomeSearchResultItem(
                section="medications",
                item_id=item.id,
                title=item.name,
                subtitle=f"{item.dosage} • {item.frequency}",
                route=f"/tracking/medications/{item.id}",
            )
        )

    logger.info("Homescreen search completed", extra={"extra_fields": {"query": q, "results_count": len(results)}})

    return HomeSearchResponse(query=q, total=len(results), results=results)


@router.get("/notifications", response_model=list[HomeNotificationResponse])
async def list_home_notifications(
    is_read: Optional[bool] = Query(None, description="Filter notifications by read status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HomeNotificationResponse]:
    """List homescreen notifications for the current user."""
    query = select(HomeNotification).where(HomeNotification.user_id == user.id)

    if is_read is not None:
        query = query.where(HomeNotification.is_read == is_read)

    result = await db.execute(
        query.order_by(HomeNotification.created_at.desc()).offset(offset).limit(limit)
    )
    notifications = result.scalars().all()
    return [HomeNotificationResponse.model_validate(item) for item in notifications]


@router.post(
    "/notifications",
    response_model=HomeNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_home_notification(
    payload: HomeNotificationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeNotificationResponse:
    """Create a homescreen notification entry."""
    notification = HomeNotification(user_id=user.id, **payload.model_dump())
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return HomeNotificationResponse.model_validate(notification)


@router.patch("/notifications/{notification_id}/read", response_model=HomeNotificationResponse)
async def mark_home_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeNotificationResponse:
    """Mark a homescreen notification as read."""
    result = await db.execute(
        select(HomeNotification).where(
            HomeNotification.id == notification_id,
            HomeNotification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(notification)

    return HomeNotificationResponse.model_validate(notification)


@router.get("/preferences", response_model=HomePreferenceResponse)
async def get_home_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomePreferenceResponse:
    """Get homescreen preference settings for the current user."""
    pref = await _get_or_create_preference(db, user.id)
    return HomePreferenceResponse.model_validate(pref)


@router.put("/preferences/theme", response_model=HomePreferenceResponse)
async def update_home_theme_preference(
    payload: HomeThemeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomePreferenceResponse:
    """Update homescreen theme mode (light, dark, or system)."""
    pref = await _get_or_create_preference(db, user.id)
    pref.theme_mode = payload.theme_mode
    await db.flush()
    await db.refresh(pref)
    return HomePreferenceResponse.model_validate(pref)
