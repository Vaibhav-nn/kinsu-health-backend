"""Homescreen endpoints — overview, search, notifications, and preferences."""

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1._utils import apply_profile_scope
from app.api.deps import ProfileScope, get_current_user, get_profile_scope
from app.models.appointment import Appointment
from app.core.database import get_db
from app.models.home import HomeNotification, HomePreference
from app.models.medication import Medication
from app.models.medication_dose_log import MedicationDoseLog
from app.models.symptom import ChronicSymptom
from app.models.user import User
from app.models.vault import HealthRecord
from app.models.vital import VitalLog
from app.schemas.homescreen import (
    HomeAnimationConfig,
    HomeAppointmentCard,
    HomeBottomNavItem,
    HomeDashboardResponse,
    HomeInsightCard,
    HomeMedicationItem,
    HomeNotificationCreate,
    HomeNotificationResponse,
    HomeOverviewResponse,
    HomePreferenceResponse,
    HomeQuickCard,
    HomeRecentRecordCard,
    HomeSearchResponse,
    HomeSearchResultItem,
    HomeThemeUpdate,
    HomeTopBarData,
    HomeTopBarProfile,
)

router = APIRouter(prefix="/homescreen", tags=["Homescreen"])


def _normalize_theme_mode(value: str) -> str:
    return value if value in {"light", "dark", "system"} else "system"


def _get_or_create_preference(db: Session, user_id: int) -> HomePreference:
    pref = db.query(HomePreference).filter(HomePreference.user_id == user_id).first()
    if pref is None:
        pref = HomePreference(user_id=user_id, theme_mode="system")
        db.add(pref)
        db.commit()
        db.refresh(pref)
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


def _format_delta(entries: list[VitalLog]) -> tuple[str, str]:
    if not entries:
        return "--", "→ 0%"
    latest = entries[0]
    if latest.vital_type == "blood_pressure" and latest.value_secondary is not None:
        value = f"{latest.value:g}/{latest.value_secondary:g}"
    else:
        value = f"{latest.value:g}"

    if len(entries) < 2:
        return value, "→ 0%"
    previous = entries[1].value
    if abs(previous) < 0.0001:
        return value, "→ 0%"
    delta = ((latest.value - previous) / previous) * 100
    if abs(delta) < 0.1:
        return value, "→ 0%"
    arrow = "↑" if delta > 0 else "↓"
    return value, f"{arrow} {abs(round(delta))}%"


@router.get("/overview", response_model=HomeOverviewResponse)
async def homescreen_overview(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeOverviewResponse:
    """Get homescreen payload for top bar, animation, quick cards, and nav."""
    pref = _get_or_create_preference(db, user.id)
    unread_count = (
        db.query(HomeNotification)
        .filter(HomeNotification.user_id == user.id, HomeNotification.is_read.is_(False))
        .count()
    )

    latest_vital = (
        apply_profile_scope(
            db.query(VitalLog),
            VitalLog,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .order_by(VitalLog.recorded_at.desc())
        .first()
    )
    active_symptoms = (
        apply_profile_scope(
            db.query(ChronicSymptom),
            ChronicSymptom,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(ChronicSymptom.is_active.is_(True))
        .count()
    )
    active_medications = (
        apply_profile_scope(
            db.query(Medication),
            Medication,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Medication.is_active.is_(True))
        .count()
    )

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
            active_profile_type=profile_scope.profile_type,
            active_profile_id=profile_scope.family_member_id,
            active_profile_label=profile_scope.profile_label,
        ),
        top_half_animation=_resolve_animation(active_symptoms, active_medications),
        cards=cards,
        bottom_nav=bottom_nav,
    )


@router.get("/dashboard", response_model=HomeDashboardResponse)
async def homescreen_dashboard(
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeDashboardResponse:
    appointments = (
        apply_profile_scope(
            db.query(Appointment),
            Appointment,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Appointment.status == "scheduled")
        .order_by(Appointment.appointment_at.asc())
        .limit(10)
        .all()
    )

    medications = (
        apply_profile_scope(
            db.query(Medication),
            Medication,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(Medication.is_active.is_(True))
        .order_by(Medication.created_at.asc())
        .limit(10)
        .all()
    )
    dose_logs = (
        apply_profile_scope(
            db.query(MedicationDoseLog),
            MedicationDoseLog,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(MedicationDoseLog.scheduled_for == datetime.now(timezone.utc).date())
        .order_by(MedicationDoseLog.updated_at.desc())
        .all()
    )
    dose_by_medication = Counter()
    latest_status_by_medication: dict[int, str] = {}
    taken = missed = left = 0
    for item in dose_logs:
        latest_status_by_medication.setdefault(item.medication_id, item.status)
        if item.status == "taken":
            taken += 1
        elif item.status == "missed":
            missed += 1
        else:
            left += 1
        dose_by_medication[item.medication_id] += 1

    medication_items = [
        HomeMedicationItem(
            id=med.id,
            name=med.name,
            dosage=med.dosage,
            subtitle=(
                f"{med.frequency.replace('_', ' ').title()}"
                + (f" · {med.prescribing_doctor}" if med.prescribing_doctor else "")
            ),
            status=latest_status_by_medication.get(med.id, "pending"),  # type: ignore[arg-type]
            scheduled_label=f"{dose_by_medication.get(med.id, 0)} dose(s) today",
        )
        for med in medications
    ]

    insights: list[HomeInsightCard] = []
    for key, title in [("blood_sugar", "Blood Sugar"), ("blood_pressure", "Blood Pressure")]:
        entries = (
            apply_profile_scope(
                db.query(VitalLog),
                VitalLog,
                user_id=user.id,
                family_member_id=profile_scope.family_member_id,
            )
            .filter(VitalLog.vital_type == key)
            .order_by(VitalLog.recorded_at.desc())
            .limit(2)
            .all()
        )
        metric, delta = _format_delta(entries)
        trend = "flat"
        if delta.startswith("↑"):
            trend = "up"
        elif delta.startswith("↓"):
            trend = "down"
        summary = (
            "No readings yet."
            if not entries
            else ("Doing well this week." if trend != "up" else "A bit high this week — let's watch it.")
        )
        insights.append(
            HomeInsightCard(
                key=key,
                title=title,
                metric=metric,
                delta_label=delta,
                summary=summary,
                trend=trend,  # type: ignore[arg-type]
            )
        )

    recent_records = (
        apply_profile_scope(
            db.query(HealthRecord),
            HealthRecord,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .order_by(HealthRecord.record_date.desc(), HealthRecord.created_at.desc())
        .limit(6)
        .all()
    )
    notifications = (
        db.query(HomeNotification)
        .filter(HomeNotification.user_id == user.id)
        .order_by(HomeNotification.created_at.desc())
        .limit(10)
        .all()
    )
    ai_alert = next(
        (
            HomeNotificationResponse.model_validate(item)
            for item in notifications
            if item.notification_type in {"ai", "insight"}
        ),
        None,
    )
    return HomeDashboardResponse(
        streak_day=max(len(recent_records) + len(dose_logs), 1),
        ai_alert=ai_alert,
        appointments=[
            HomeAppointmentCard(
                id=item.id,
                doctor_name=item.doctor_name,
                specialty=item.specialty,
                appointment_at=item.appointment_at,
                location=item.location,
                status=item.status,
                notes=item.notes,
            )
            for item in appointments
        ],
        medications_taken=taken,
        medications_missed=missed,
        medications_left=left or max(len(medications) - taken - missed, 0),
        medication_items=medication_items,
        insights=insights,
        recent_records=[
            HomeRecentRecordCard(
                id=item.id,
                title=item.title,
                subtitle=" · ".join(part for part in [item.provider_name, item.record_date.strftime("%d %b %Y")] if part),
                record_type=item.record_type,
                record_date=datetime.combine(item.record_date, datetime.min.time(), tzinfo=timezone.utc),
            )
            for item in recent_records
        ],
        notifications=[HomeNotificationResponse.model_validate(item) for item in notifications],
    )


@router.get("/search", response_model=HomeSearchResponse)
async def homescreen_search(
    q: str = Query(..., min_length=1, max_length=120, description="Search query"),
    user: User = Depends(get_current_user),
    profile_scope: ProfileScope = Depends(get_profile_scope),
    db: Session = Depends(get_db),
) -> HomeSearchResponse:
    """Search across vitals, symptoms, and medications for homescreen results."""
    term = q.strip()
    if not term:
        return HomeSearchResponse(query=q, total=0, results=[])

    pattern = f"%{term}%"
    results: list[HomeSearchResultItem] = []

    vitals = (
        apply_profile_scope(
            db.query(VitalLog),
            VitalLog,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            or_(
                VitalLog.vital_type.ilike(pattern),
                VitalLog.notes.ilike(pattern),
                VitalLog.unit.ilike(pattern),
            ),
        )
        .order_by(VitalLog.recorded_at.desc())
        .limit(10)
        .all()
    )

    for item in vitals:
        results.append(
            HomeSearchResultItem(
                section="vitals",
                item_id=str(item.id),
                title=item.vital_type.replace("_", " ").title(),
                subtitle=f"{item.value:g} {item.unit}",
                route=f"/tracking/vitals/{item.id}",
            )
        )

    symptoms = (
        apply_profile_scope(
            db.query(ChronicSymptom),
            ChronicSymptom,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            or_(
                ChronicSymptom.symptom_name.ilike(pattern),
                ChronicSymptom.body_area.ilike(pattern),
                ChronicSymptom.triggers.ilike(pattern),
                ChronicSymptom.notes.ilike(pattern),
            ),
        )
        .order_by(ChronicSymptom.updated_at.desc())
        .limit(10)
        .all()
    )

    for item in symptoms:
        results.append(
            HomeSearchResultItem(
                section="symptoms",
                item_id=str(item.id),
                title=item.symptom_name.replace("_", " ").title(),
                subtitle=f"Severity {item.severity}/10",
                route=f"/tracking/symptoms/{item.id}",
            )
        )

    medications = (
        apply_profile_scope(
            db.query(Medication),
            Medication,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            or_(
                Medication.name.ilike(pattern),
                Medication.dosage.ilike(pattern),
                Medication.prescribing_doctor.ilike(pattern),
                Medication.notes.ilike(pattern),
            ),
        )
        .order_by(Medication.updated_at.desc())
        .limit(10)
        .all()
    )

    for item in medications:
        results.append(
            HomeSearchResultItem(
                section="medications",
                item_id=str(item.id),
                title=item.name,
                subtitle=f"{item.dosage} • {item.frequency}",
                route=f"/tracking/medications/{item.id}",
            )
        )

    records = (
        apply_profile_scope(
            db.query(HealthRecord),
            HealthRecord,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            or_(
                HealthRecord.title.ilike(pattern),
                HealthRecord.notes.ilike(pattern),
                HealthRecord.record_type.ilike(pattern),
                HealthRecord.provider_name.ilike(pattern),
                HealthRecord.document_subtype.ilike(pattern),
            ),
        )
        .order_by(HealthRecord.record_date.desc(), HealthRecord.created_at.desc())
        .limit(10)
        .all()
    )

    for item in records:
        subtitle_parts = [
            item.provider_name,
            item.record_date.strftime("%d %b %Y"),
        ]
        results.append(
            HomeSearchResultItem(
                section="records",
                item_id=str(item.id),
                title=item.title,
                subtitle=" · ".join(part for part in subtitle_parts if part),
                route=f"/vault/records/{item.id}",
            )
        )

    appointments = (
        apply_profile_scope(
            db.query(Appointment),
            Appointment,
            user_id=user.id,
            family_member_id=profile_scope.family_member_id,
        )
        .filter(
            or_(
                Appointment.doctor_name.ilike(pattern),
                Appointment.specialty.ilike(pattern),
                Appointment.location.ilike(pattern),
                Appointment.notes.ilike(pattern),
            ),
        )
        .order_by(Appointment.appointment_at.asc())
        .limit(10)
        .all()
    )

    for item in appointments:
        subtitle_parts = [
            item.specialty,
            item.location,
        ]
        results.append(
            HomeSearchResultItem(
                section="appointments",
                item_id=str(item.id),
                title=item.doctor_name,
                subtitle=" · ".join(part for part in subtitle_parts if part),
                route=f"/appointments/{item.id}",
            )
        )

    return HomeSearchResponse(query=q, total=len(results), results=results)


@router.get("/notifications", response_model=list[HomeNotificationResponse])
async def list_home_notifications(
    is_read: Optional[bool] = Query(None, description="Filter notifications by read status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HomeNotificationResponse]:
    """List homescreen notifications for the current user."""
    query = db.query(HomeNotification).filter(HomeNotification.user_id == user.id)

    if is_read is not None:
        query = query.filter(HomeNotification.is_read == is_read)

    notifications = query.order_by(HomeNotification.created_at.desc()).offset(offset).limit(limit).all()
    return [HomeNotificationResponse.model_validate(item) for item in notifications]


@router.post(
    "/notifications",
    response_model=HomeNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_home_notification(
    payload: HomeNotificationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeNotificationResponse:
    """Create a homescreen notification entry."""
    notification = HomeNotification(user_id=user.id, **payload.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return HomeNotificationResponse.model_validate(notification)


@router.patch("/notifications/{notification_id}/read", response_model=HomeNotificationResponse)
async def mark_home_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeNotificationResponse:
    """Mark a homescreen notification as read."""
    notification = db.query(HomeNotification).filter(
        HomeNotification.id == notification_id,
        HomeNotification.user_id == user.id,
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return HomeNotificationResponse.model_validate(notification)


@router.get("/preferences", response_model=HomePreferenceResponse)
async def get_home_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomePreferenceResponse:
    """Get homescreen preference settings for the current user."""
    pref = _get_or_create_preference(db, user.id)
    return HomePreferenceResponse.model_validate(pref)


@router.put("/preferences/theme", response_model=HomePreferenceResponse)
async def update_home_theme_preference(
    payload: HomeThemeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomePreferenceResponse:
    """Update homescreen theme mode (light, dark, or system)."""
    pref = _get_or_create_preference(db, user.id)
    pref.theme_mode = payload.theme_mode
    db.commit()
    db.refresh(pref)
    return HomePreferenceResponse.model_validate(pref)
