"""Pydantic schemas for all health features.

Grouped by feature: Vitals, Symptoms, Illness, Medications, Reminders.
"""

from datetime import date, datetime, time
from typing import Optional

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

    details: list[IllnessDetailResponse] = []


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
