"""Pydantic schemas for homescreen APIs."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ThemeMode = Literal["light", "dark", "system"]


class HomePreferenceResponse(BaseModel):
    """Homescreen preference response."""

    id: int
    theme_mode: ThemeMode
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HomeThemeUpdate(BaseModel):
    """Payload for updating theme preference."""

    theme_mode: ThemeMode


class HomeNotificationCreate(BaseModel):
    """Payload to create a homescreen notification."""

    title: str = Field(..., examples=["Medication reminder"])
    body: str = Field(..., examples=["Time to take Metformin 500mg"])
    notification_type: str = Field("general", examples=["general", "vitals", "medication"])
    action_route: Optional[str] = Field(None, examples=["/tracking/medications"])


class HomeNotificationResponse(BaseModel):
    """Homescreen notification response."""

    id: int
    notification_type: str
    title: str
    body: str
    action_route: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HomeTopBarProfile(BaseModel):
    """Top-bar profile block."""

    display_name: str
    email: str
    initials: str


class HomeTopBarData(BaseModel):
    """Top section bar payload."""

    search_placeholder: str
    notification_unread_count: int
    theme_mode: ThemeMode
    profile: HomeTopBarProfile
    active_profile_type: str = "self"
    active_profile_id: Optional[int] = None
    active_profile_label: Optional[str] = None


class HomeAnimationConfig(BaseModel):
    """Config for rendering top-half homescreen animation."""

    animation_key: str
    headline: str
    subheadline: str


class HomeQuickCard(BaseModel):
    """Homescreen quick-access card."""

    key: str
    title: str
    value: str
    subtitle: str
    route: str


class HomeBottomNavItem(BaseModel):
    """Bottom navigation item configuration."""

    key: str
    label: str
    route: str
    is_active: bool = False


class HomeOverviewResponse(BaseModel):
    """Main homescreen response payload."""

    top_bar: HomeTopBarData
    top_half_animation: HomeAnimationConfig
    cards: list[HomeQuickCard]
    bottom_nav: list[HomeBottomNavItem]


class HomeAppointmentCard(BaseModel):
    id: int
    doctor_name: str
    specialty: Optional[str] = None
    appointment_at: datetime
    location: Optional[str] = None
    status: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    doctor_name: str = Field(..., min_length=1, max_length=255)
    specialty: Optional[str] = Field(default=None, max_length=128)
    appointment_at: datetime
    location: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="scheduled", max_length=32)
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    doctor_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    specialty: Optional[str] = Field(default=None, max_length=128)
    appointment_at: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None


class HomeMedicationItem(BaseModel):
    id: int
    name: str
    dosage: str
    subtitle: str
    status: Literal["taken", "missed", "pending"]
    scheduled_label: Optional[str] = None


class HomeInsightCard(BaseModel):
    key: str
    title: str
    metric: str
    delta_label: str
    summary: str
    trend: Literal["up", "down", "flat"]


class HomeRecentRecordCard(BaseModel):
    id: str
    title: str
    subtitle: str
    record_type: str
    record_date: datetime


class HomeDashboardResponse(BaseModel):
    streak_day: int
    ai_alert: Optional[HomeNotificationResponse] = None
    appointments: list[HomeAppointmentCard]
    medications_taken: int
    medications_missed: int
    medications_left: int
    medication_items: list[HomeMedicationItem]
    insights: list[HomeInsightCard]
    recent_records: list[HomeRecentRecordCard]
    notifications: list[HomeNotificationResponse]


class HomeSearchResultItem(BaseModel):
    """Search result item across homescreen-backed resources."""

    section: str
    item_id: str
    title: str
    subtitle: str
    route: str


class HomeSearchResponse(BaseModel):
    """Global homescreen search response."""

    query: str
    total: int
    results: list[HomeSearchResultItem]
