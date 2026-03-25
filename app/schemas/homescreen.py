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


class HomeSearchResultItem(BaseModel):
    """Search result item across homescreen-backed resources."""

    section: str
    item_id: int
    title: str
    subtitle: str
    route: str


class HomeSearchResponse(BaseModel):
    """Global homescreen search response."""

    query: str
    total: int
    results: list[HomeSearchResultItem]
