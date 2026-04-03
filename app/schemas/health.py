"""Pydantic schemas for all health features.

Grouped by feature: Vitals, Symptoms, Illness, Medications, Reminders.
"""

from datetime import date, datetime, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════
#  VITALS
# ══════════════════════════════════════════════════════════

class VitalLogCreate(BaseModel):
    """Payload to log a new vital reading."""

    vital_type: str = Field(..., examples=["heart_rate", "blood_pressure", "spo2", "temperature", "weight"])
    value: float = Field(..., examples=[72.0])
    value_secondary: Optional[float] = Field(None, examples=[80.0], description="e.g. diastolic for BP")
    unit: str = Field(..., examples=["bpm", "mmHg", "%", "°C", "kg"])
    recorded_at: datetime
    notes: Optional[str] = None


class VitalLogResponse(BaseModel):
    """Single vital reading response."""

    id: int
    family_member_id: Optional[int] = None
    vital_type: str
    value: float
    value_secondary: Optional[float] = None
    unit: str
    recorded_at: datetime
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VitalTrendPoint(BaseModel):
    """A single data point in a vital trend chart."""

    recorded_at: datetime
    value: float
    value_secondary: Optional[float] = None


class VitalTrendResponse(BaseModel):
    """Aggregated trend data for a specific vital type."""

    vital_type: str
    unit: str
    data_points: list[VitalTrendPoint]
    count: int
    avg_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class VitalSnapshotCreate(BaseModel):
    recorded_at: datetime
    notes: Optional[str] = None
    blood_pressure_systolic: Optional[float] = None
    blood_pressure_diastolic: Optional[float] = None
    blood_sugar: Optional[float] = None
    heart_rate: Optional[float] = None
    weight: Optional[float] = None
    temperature: Optional[float] = None
    spo2: Optional[float] = None


class VitalTodayCard(BaseModel):
    vital_type: str
    label: str
    latest_value: str
    unit: str
    delta_label: str


# ══════════════════════════════════════════════════════════
#  CHRONIC SYMPTOMS
# ══════════════════════════════════════════════════════════

class SymptomCreate(BaseModel):
    """Payload to add a chronic symptom."""

    symptom_name: str = Field(..., examples=["migraine", "joint_pain"])
    severity: int = Field(..., ge=1, le=10)
    frequency: str = Field(..., examples=["daily", "weekly", "monthly", "intermittent"])
    body_area: Optional[str] = Field(None, examples=["head", "lower_back"])
    triggers: Optional[str] = None
    first_noticed: date
    is_active: bool = True
    notes: Optional[str] = None


class SymptomUpdate(BaseModel):
    """Payload to update a chronic symptom (partial update)."""

    symptom_name: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=10)
    frequency: Optional[str] = None
    body_area: Optional[str] = None
    triggers: Optional[str] = None
    first_noticed: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SymptomResponse(BaseModel):
    """Chronic symptom response."""

    id: int
    family_member_id: Optional[int] = None
    symptom_name: str
    severity: int
    frequency: str
    body_area: Optional[str] = None
    triggers: Optional[str] = None
    first_noticed: date
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SymptomEventCreate(BaseModel):
    symptom_name: str
    severity: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None
    occurred_at: Optional[datetime] = None


class SymptomEventResponse(BaseModel):
    id: int
    symptom_name: str
    severity: int
    notes: Optional[str] = None
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SymptomWeeklyPattern(BaseModel):
    weekday: str
    count: int


class SymptomDashboardItem(BaseModel):
    symptom_name: str
    severity_label: str
    frequency_label: str
    trend: Literal["improving", "stable", "worsening"]
    pattern: list[SymptomWeeklyPattern]


# ══════════════════════════════════════════════════════════
#  ILLNESS EPISODES
# ══════════════════════════════════════════════════════════

class IllnessDetailCreate(BaseModel):
    """Payload to add a detail entry to an illness episode."""

    detail_type: str = Field(..., examples=["symptom", "diagnosis", "treatment", "note"])
    content: str
    recorded_at: Optional[datetime] = None


class IllnessDetailResponse(BaseModel):
    """Single detail entry within an episode."""

    id: int
    detail_type: str
    content: str
    recorded_at: datetime

    class Config:
        from_attributes = True


class IllnessEpisodeCreate(BaseModel):
    """Payload to create an illness episode."""

    title: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    status: str = Field("active", examples=["active", "recovered", "chronic"])


class IllnessEpisodeUpdate(BaseModel):
    """Payload to update an illness episode (partial update)."""

    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class IllnessEpisodeResponse(BaseModel):
    """Illness episode response (without details)."""

    id: int
    family_member_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IllnessEpisodeDetailedResponse(IllnessEpisodeResponse):
    """Illness episode with all detail entries (detailed view)."""

    details: list[IllnessDetailResponse] = Field(default_factory=list)


class IllnessDashboardCard(BaseModel):
    id: int
    title: str
    subtitle: str
    status: str
    tags: list[str]
    consult_count: int = 0
    report_count: int = 0


# ══════════════════════════════════════════════════════════
#  MEDICATIONS
# ══════════════════════════════════════════════════════════

class MedicationCreate(BaseModel):
    """Payload to add a medication."""

    name: str
    dosage: str = Field(..., examples=["500mg", "10ml"])
    frequency: str = Field(..., examples=["once_daily", "twice_daily", "as_needed"])
    route: str = Field("oral", examples=["oral", "topical", "injection", "inhaled"])
    start_date: date
    end_date: Optional[date] = None
    prescribing_doctor: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class MedicationUpdate(BaseModel):
    """Payload to update a medication (partial update)."""

    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribing_doctor: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class MedicationResponse(BaseModel):
    """Medication response."""

    id: int
    family_member_id: Optional[int] = None
    name: str
    dosage: str
    frequency: str
    route: str
    start_date: date
    end_date: Optional[date] = None
    prescribing_doctor: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicationDoseLogCreate(BaseModel):
    scheduled_for: date
    scheduled_time: Optional[time] = None
    status: Literal["taken", "missed", "pending"]
    taken_at: Optional[datetime] = None
    notes: Optional[str] = None


class MedicationDoseLogResponse(BaseModel):
    id: int
    medication_id: int
    scheduled_for: date
    scheduled_time: Optional[time] = None
    status: str
    taken_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class MedicationDashboardItem(BaseModel):
    medication: MedicationResponse
    adherence_pct: int
    latest_status: Literal["taken", "missed", "pending"]
    schedule_label: Optional[str] = None


class MedicationDashboardResponse(BaseModel):
    taken: int
    missed: int
    left: int
    adherence_pct: int
    items: list[MedicationDashboardItem]


class MedicationWeeklyMatrixEntry(BaseModel):
    medication_id: int
    medication_name: str
    dosage: str
    day_statuses: list[str]


class MedicationMonthlyCalendarDay(BaseModel):
    day: int
    adherence_bucket: Literal["high", "medium", "low", "none"]


class MedicationAdherenceResponse(BaseModel):
    view: Literal["daily", "weekly", "monthly"]
    weekly_rows: list[MedicationWeeklyMatrixEntry] = Field(default_factory=list)
    monthly_days: list[MedicationMonthlyCalendarDay] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════
#  REMINDERS
# ══════════════════════════════════════════════════════════

class ReminderCreate(BaseModel):
    """Payload to create a reminder."""

    title: str
    reminder_type: str = Field(..., examples=["medication", "appointment", "checkup", "custom"])
    linked_medication_id: Optional[int] = None
    scheduled_time: time
    recurrence: str = Field("daily", examples=["daily", "weekly", "monthly", "once"])
    is_enabled: bool = True
    notes: Optional[str] = None


class ReminderUpdate(BaseModel):
    """Payload to update a reminder (partial update)."""

    title: Optional[str] = None
    reminder_type: Optional[str] = None
    linked_medication_id: Optional[int] = None
    scheduled_time: Optional[time] = None
    recurrence: Optional[str] = None
    is_enabled: Optional[bool] = None
    notes: Optional[str] = None


class ReminderResponse(BaseModel):
    """Reminder response."""

    id: int
    family_member_id: Optional[int] = None
    title: str
    reminder_type: str
    linked_medication_id: Optional[int] = None
    scheduled_time: time
    recurrence: str
    is_enabled: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityLogCreate(BaseModel):
    category: str
    activity_name: str
    duration_minutes: int = Field(..., ge=1, le=1440)
    calories_burned: Optional[int] = Field(default=None, ge=0)
    distance_km: Optional[float] = Field(default=None, ge=0)
    details: Optional[dict[str, Any]] = None
    logged_at: Optional[datetime] = None


class ActivityLogResponse(BaseModel):
    id: int
    category: str
    activity_name: str
    duration_minutes: int
    calories_burned: int
    distance_km: Optional[float] = None
    details: Optional[dict[str, Any]] = None
    logged_at: datetime

    class Config:
        from_attributes = True


class ActivitySummaryResponse(BaseModel):
    calories: int
    duration_minutes: int
    activities_done: int
    today: list[ActivityLogResponse]


class ActivityHistoryBar(BaseModel):
    weekday: str
    calories: int


class ActivityHistoryResponse(BaseModel):
    weekly_calories: list[ActivityHistoryBar]
    active_days: int
    total_weekly_calories: int


class ActivityRecommendationItem(BaseModel):
    title: str
    subtitle: str
    duration_minutes: int
    recommendation_reason: str
    risk_level: str


class ActivityRecommendationResponse(BaseModel):
    summary: str
    items: list[ActivityRecommendationItem]


class ActivityCatalogItem(BaseModel):
    category: str
    activity_name: str
    estimated_calories: int
    duration_minutes: int
    fields: list[str] = Field(default_factory=list)


class ActivityCatalogSection(BaseModel):
    category: str
    title: str
    items: list[ActivityCatalogItem] = Field(default_factory=list)
