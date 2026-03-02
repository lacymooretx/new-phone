import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field

# ── Shift schemas ──


class WfmShiftCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    start_time: time
    end_time: time
    break_minutes: int = Field(60, ge=0, le=480)
    color: str | None = Field(None, max_length=7)


class WfmShiftUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    start_time: time | None = None
    end_time: time | None = None
    break_minutes: int | None = Field(None, ge=0, le=480)
    color: str | None = None
    is_active: bool | None = None


class WfmShiftResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    start_time: time
    end_time: time
    break_minutes: int
    color: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Schedule entry schemas ──


class WfmScheduleEntryCreate(BaseModel):
    extension_id: uuid.UUID
    shift_id: uuid.UUID
    date: date
    notes: str | None = None


class WfmScheduleEntryBulkCreate(BaseModel):
    entries: list[WfmScheduleEntryCreate] = Field(..., min_length=1, max_length=500)


class WfmScheduleEntryUpdate(BaseModel):
    shift_id: uuid.UUID | None = None
    notes: str | None = None


class WfmScheduleEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_id: uuid.UUID
    shift_id: uuid.UUID
    date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # Nested shift info
    shift: WfmShiftResponse | None = None
    # Denormalized extension fields
    extension_number: str = ""
    extension_name: str = ""


# ── Time-off schemas ──


class WfmTimeOffRequestCreate(BaseModel):
    extension_id: uuid.UUID
    start_date: date
    end_date: date
    reason: str | None = None


class WfmTimeOffReview(BaseModel):
    status: str = Field(..., pattern="^(approved|denied)$")
    review_notes: str | None = None


class WfmTimeOffRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_id: uuid.UUID
    start_date: date
    end_date: date
    reason: str | None
    status: str
    reviewed_by_id: uuid.UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime
    # Denormalized
    extension_number: str = ""
    extension_name: str = ""


# ── Forecast config schemas ──


class WfmForecastConfigCreate(BaseModel):
    queue_id: uuid.UUID
    target_sla_percent: int = Field(80, ge=1, le=100)
    target_sla_seconds: int = Field(20, ge=1, le=600)
    shrinkage_percent: int = Field(30, ge=0, le=80)
    lookback_weeks: int = Field(8, ge=1, le=52)


class WfmForecastConfigUpdate(BaseModel):
    target_sla_percent: int | None = Field(None, ge=1, le=100)
    target_sla_seconds: int | None = Field(None, ge=1, le=600)
    shrinkage_percent: int | None = Field(None, ge=0, le=80)
    lookback_weeks: int | None = Field(None, ge=1, le=52)


class WfmForecastConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    queue_id: uuid.UUID
    target_sla_percent: int
    target_sla_seconds: int
    shrinkage_percent: int
    lookback_weeks: int
    created_at: datetime
    updated_at: datetime
    # Denormalized
    queue_name: str = ""


# ── Analytics schemas ──


class WfmHourlyVolume(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    avg_calls: float
    avg_aht_seconds: float
    avg_abandon_rate: float


class WfmDailyVolume(BaseModel):
    day_of_week: str
    avg_calls: float
    avg_aht_seconds: float


class WfmForecastPoint(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    predicted_calls: float
    recommended_agents: int
    target_sla_percent: int
    target_sla_seconds: int


class WfmStaffingSummary(BaseModel):
    queue_id: uuid.UUID
    queue_name: str
    current_agents: int
    recommended_agents: int
    forecast_volume: float


class WfmScheduleOverview(BaseModel):
    date: date
    total_scheduled: int
    time_off_approved: int
    net_available: int
