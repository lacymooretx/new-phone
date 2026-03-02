import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OriginateRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=40)
    caller_extension_id: uuid.UUID | None = None
    originate_timeout: int = Field(30, ge=5, le=120)


class OriginateResponse(BaseModel):
    status: str
    destination: str
    caller_extension: str


class NumberHistoryEntry(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    direction: str
    caller_number: str
    caller_name: str
    called_number: str
    disposition: str
    duration_seconds: int
    start_time: datetime


class ExtensionLookupResponse(BaseModel):
    extension_id: uuid.UUID | None = None
    extension_number: str | None = None
    display_name: str | None = None
    dnd_enabled: bool = False
    agent_status: str | None = None
    is_internal: bool = False


class ActiveCallEntry(BaseModel):
    """A single active call/channel from FreeSWITCH."""

    uuid: str
    direction: str
    caller_name: str
    caller_number: str
    destination: str
    state: str
    callstate: str
    read_codec: str
    write_codec: str
    secure: str
    created: str
    created_epoch: str
    hostname: str
    context: str


class ActiveCallsResponse(BaseModel):
    """Response for the active calls endpoint."""

    total: int
    channels: list[ActiveCallEntry]


class FreeSwitchMetrics(BaseModel):
    """FreeSWITCH system metrics."""

    active_channels: int = 0
    calls_per_second: float = 0.0
    registrations_total: int = 0
    sessions_since_startup: int = 0
    sessions_peak: int = 0
    sessions_peak_5min: int = 0
    sessions_max: int = 0
    current_sessions: int = 0
