import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimeConditionRule(BaseModel):
    type: str = Field(..., description="day_of_week, time_of_day, specific_date, date_range")
    days: list[int] | None = Field(None, description="Day numbers (1=Mon, 7=Sun) for day_of_week")
    start_time: str | None = Field(None, description="HH:MM for time_of_day")
    end_time: str | None = Field(None, description="HH:MM for time_of_day")
    start_date: str | None = Field(None, description="YYYY-MM-DD for specific_date or date_range")
    end_date: str | None = Field(None, description="YYYY-MM-DD for date_range")
    invert: bool = False
    label: str | None = None


class TimeConditionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    timezone: str = "America/New_York"
    rules: list[TimeConditionRule] = Field(default_factory=list)
    match_destination_type: str
    match_destination_id: uuid.UUID | None = None
    nomatch_destination_type: str
    nomatch_destination_id: uuid.UUID | None = None
    holiday_calendar_id: uuid.UUID | None = None
    enabled: bool = True
    site_id: uuid.UUID | None = None


class TimeConditionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    timezone: str | None = None
    rules: list[TimeConditionRule] | None = None
    match_destination_type: str | None = None
    match_destination_id: uuid.UUID | None = None
    nomatch_destination_type: str | None = None
    nomatch_destination_id: uuid.UUID | None = None
    holiday_calendar_id: uuid.UUID | None = None
    manual_override: str | None = None
    enabled: bool | None = None
    site_id: uuid.UUID | None = None


class TimeConditionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    timezone: str
    rules: list[dict[str, Any]]
    match_destination_type: str
    match_destination_id: uuid.UUID | None
    nomatch_destination_type: str
    nomatch_destination_id: uuid.UUID | None
    holiday_calendar_id: uuid.UUID | None = None
    manual_override: str | None = None
    site_id: uuid.UUID | None = None
    enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
