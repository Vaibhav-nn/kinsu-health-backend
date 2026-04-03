"""Exercise and activity APIs for track recommendations and logging."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope, get_user_owned_or_404
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.core.database import get_db
from app.models.activity import ActivityLog
from app.models.medication import Medication
from app.models.user import User
from app.schemas.health import (
    ActivityCatalogItem,
    ActivityCatalogSection,
    ActivityHistoryBar,
    ActivityHistoryResponse,
    ActivityLogCreate,
    ActivityLogResponse,
    ActivityRecommendationItem,
    ActivityRecommendationResponse,
    ActivitySummaryResponse,
)

router = APIRouter(prefix="/exercise", tags=["Exercise"])

_ACTIVITY_CATALOG: dict[str, tuple[str, list[tuple[str, int, int, list[str]]]]] = {
    "cardio": (
        "Cardio",
        [
            ("Treadmill", 159, 20, ["duration_minutes", "incline", "speed"]),
            ("Jumping Jacks", 181, 20, ["duration_minutes"]),
            ("Burpees", 227, 20, ["duration_minutes"]),
            ("Jump Rope", 249, 20, ["duration_minutes"]),
            ("High Knees", 204, 20, ["duration_minutes"]),
            ("Mountain Climbers", 204, 20, ["duration_minutes"]),
        ],
    ),
    "strength": (
        "Strength",
        [
            ("Push-ups", 91, 20, ["duration_minutes", "reps"]),
            ("Pull-ups", 113, 20, ["duration_minutes", "reps"]),
            ("Squats", 113, 20, ["duration_minutes", "reps"]),
            ("Lunges", 91, 20, ["duration_minutes", "reps"]),
            ("Plank", 91, 20, ["duration_minutes"]),
            ("Deadlift", 113, 20, ["duration_minutes", "weight_kg"]),
            ("Bench Press", 113, 20, ["duration_minutes", "weight_kg"]),
        ],
    ),
    "yoga": (
        "Yoga & Pranayama",
        [
            ("Surya Namaskar", 75, 20, ["duration_minutes"]),
            ("Kapalbhati", 68, 20, ["duration_minutes"]),
            ("Anulom Vilom", 45, 20, ["duration_minutes"]),
            ("Bhujangasana", 57, 20, ["duration_minutes"]),
            ("Trikonasana", 57, 20, ["duration_minutes"]),
            ("Virabhadrasana", 68, 20, ["duration_minutes"]),
            ("Meditation", 34, 20, ["duration_minutes"]),
        ],
    ),
    "walk_run": (
        "Walk / Run",
        [
            ("Walking", 79, 20, ["duration_minutes", "distance_km"]),
            ("Brisk Walking", 113, 20, ["duration_minutes", "distance_km"]),
            ("Running", 204, 20, ["duration_minutes", "distance_km"]),
            ("Jogging", 159, 20, ["duration_minutes", "distance_km"]),
            ("Stairs Climbing", 136, 20, ["duration_minutes"]),
        ],
    ),
    "cycling": (
        "Cycling",
        [
            ("Outdoor Cycling", 159, 20, ["duration_minutes", "distance_km"]),
            ("Stationary Bike", 159, 20, ["duration_minutes"]),
        ],
    ),
    "other": (
        "Other",
        [
            ("Swimming", 181, 20, ["duration_minutes"]),
            ("HIIT", 227, 20, ["duration_minutes"]),
            ("Stretching", 57, 20, ["duration_minutes"]),
            ("Dance", 136, 20, ["duration_minutes"]),
            ("Cricket", 113, 20, ["duration_minutes"]),
            ("Badminton", 125, 20, ["duration_minutes"]),
        ],
    ),
}


def _daily_window(anchor: date) -> tuple[datetime, datetime]:
    start = datetime.combine(anchor, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _calories_for_log(payload: ActivityLogCreate) -> int:
    if payload.calories_burned is not None:
        return payload.calories_burned
    duration = payload.duration_minutes
    normalized_name = payload.activity_name.strip().lower()
    for _, (_, items) in _ACTIVITY_CATALOG.items():
        for name, calories, base_minutes, _fields in items:
            if name.lower() == normalized_name:
                return max(int(round((calories / base_minutes) * duration)), 1)
    return max(duration * 5, 1)


def _recommendation_summary(active_medications: list[Medication]) -> str:
    if not active_medications:
        return "Balanced movement is ideal. Choose moderate activity and build consistency."
    names = ", ".join(med.name for med in active_medications[:3])
    return (
        f"Based on your current medications ({names}), avoid high-intensity exercise "
        "without medical advice. Low-to-moderate activity is ideal."
    )


@router.get("/catalog", response_model=list[ActivityCatalogSection])
async def activity_catalog() -> list[ActivityCatalogSection]:
    sections: list[ActivityCatalogSection] = []
    for category, (title, items) in _ACTIVITY_CATALOG.items():
        sections.append(
            ActivityCatalogSection(
                category=category,
                title=title,
                items=[
                    ActivityCatalogItem(
                        category=category,
                        activity_name=name,
                        estimated_calories=calories,
                        duration_minutes=duration,
                        fields=fields,
                    )
                    for name, calories, duration, fields in items
                ],
            )
        )
    return sections


@router.post("/logs", response_model=ActivityLogResponse, status_code=status.HTTP_201_CREATED)
async def log_activity(
    payload: ActivityLogCreate,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ActivityLogResponse:
    log = ActivityLog(
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        category=payload.category,
        activity_name=payload.activity_name,
        duration_minutes=payload.duration_minutes,
        calories_burned=_calories_for_log(payload),
        distance_km=payload.distance_km,
        details=payload.details,
        logged_at=payload.logged_at or datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ActivityLogResponse.model_validate(log)


@router.get("/logs", response_model=list[ActivityLogResponse])
async def list_activity_logs(
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> list[ActivityLogResponse]:
    query = apply_profile_scope(
        db.query(ActivityLog),
        ActivityLog,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
    )
    if category:
        query = query.filter(ActivityLog.category == category)
    items = query.order_by(ActivityLog.logged_at.desc()).offset(offset).limit(limit).all()
    return [ActivityLogResponse.model_validate(item) for item in items]


@router.get("/logs/{activity_id}", response_model=ActivityLogResponse)
async def get_activity_log(
    activity_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ActivityLogResponse:
    item = get_user_owned_or_404(
        db,
        ActivityLog,
        item_id=activity_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Activity log not found.",
    )
    return ActivityLogResponse.model_validate(item)


@router.delete("/logs/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity_log(
    activity_id: int,
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> None:
    item = get_user_owned_or_404(
        db,
        ActivityLog,
        item_id=activity_id,
        user_id=user.id,
        family_member_id=profile_scope.family_member_id,
        not_found_detail="Activity log not found.",
    )
    db.delete(item)
    db.commit()


@router.get("/summary", response_model=ActivitySummaryResponse)
async def activity_summary(
    target_date: Optional[date] = Query(default=None),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ActivitySummaryResponse:
    effective_date = target_date or date.today()
    start, end = _daily_window(effective_date)
    today_items = (
        apply_profile_scope(
            db.query(ActivityLog),
            ActivityLog,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(ActivityLog.logged_at >= start, ActivityLog.logged_at < end)
        .order_by(ActivityLog.logged_at.desc())
        .all()
    )
    return ActivitySummaryResponse(
        calories=sum(item.calories_burned for item in today_items),
        duration_minutes=sum(item.duration_minutes for item in today_items),
        activities_done=len(today_items),
        today=[ActivityLogResponse.model_validate(item) for item in today_items],
    )


@router.get("/history", response_model=ActivityHistoryResponse)
async def activity_history(
    anchor_date: Optional[date] = Query(default=None),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ActivityHistoryResponse:
    anchor = anchor_date or date.today()
    week_start = anchor - timedelta(days=anchor.weekday())
    week_end = week_start + timedelta(days=7)
    logs = (
        apply_profile_scope(
            db.query(ActivityLog),
            ActivityLog,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            ActivityLog.logged_at >= datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc),
            ActivityLog.logged_at < datetime.combine(week_end, datetime.min.time(), tzinfo=timezone.utc),
        )
        .order_by(ActivityLog.logged_at.asc())
        .all()
    )
    buckets: dict[str, int] = defaultdict(int)
    active_days: set[date] = set()
    for item in logs:
        label = item.logged_at.strftime("%a")[0]
        buckets[label] += item.calories_burned
        active_days.add(item.logged_at.date())

    ordered = ["M", "T", "W", "T", "F", "S", "S"]
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekly = [
        ActivityHistoryBar(weekday=ordered[index], calories=buckets.get(labels[index][0], 0))
        for index in range(7)
    ]
    # Rebuild with stable label mapping to avoid Tue/Thu and Sat/Sun collisions.
    weekly = [
        ActivityHistoryBar(
            weekday=ordered[index],
            calories=sum(
                item.calories_burned
                for item in logs
                if item.logged_at.strftime("%a") == labels[index]
            ),
        )
        for index in range(7)
    ]
    return ActivityHistoryResponse(
        weekly_calories=weekly,
        active_days=len(active_days),
        total_weekly_calories=sum(item.calories_burned for item in logs),
    )


@router.get("/recommendations", response_model=ActivityRecommendationResponse)
async def activity_recommendations(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> ActivityRecommendationResponse:
    active_medications = (
        apply_profile_scope(
            db.query(Medication),
            Medication,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Medication.is_active.is_(True))
        .order_by(Medication.created_at.asc())
        .all()
    )
    items = [
        ActivityRecommendationItem(
            title="Morning Walk",
            subtitle="Good for blood sugar management",
            duration_minutes=30,
            recommendation_reason="Recommended for Diabetes",
            risk_level="Low",
        ),
        ActivityRecommendationItem(
            title="Chair Yoga",
            subtitle="Safe for hypertension patients",
            duration_minutes=20,
            recommendation_reason="Recommended for Hypertension",
            risk_level="Low",
        ),
        ActivityRecommendationItem(
            title="Anulom Vilom",
            subtitle="Reduces stress and calms the nervous system",
            duration_minutes=15,
            recommendation_reason="Recommended for Stress",
            risk_level="Very Low",
        ),
    ]
    return ActivityRecommendationResponse(
        summary=_recommendation_summary(active_medications),
        items=items,
    )
