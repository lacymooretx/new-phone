import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class HolidayEntryData(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    date: date
    recur_annually: bool = False
    all_day: bool = True
    start_time: time | None = None
    end_time: time | None = None


class HolidayCalendarCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    entries: list[HolidayEntryData] = Field(default_factory=list)


class HolidayCalendarUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    entries: list[HolidayEntryData] | None = None


class HolidayEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    calendar_id: uuid.UUID
    name: str
    date: date
    recur_annually: bool
    all_day: bool
    start_time: time | None
    end_time: time | None


class HolidayCalendarResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    entries: list[HolidayEntryResponse] = []
    created_at: datetime
    updated_at: datetime
