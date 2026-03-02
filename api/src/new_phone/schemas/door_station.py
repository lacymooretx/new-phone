import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DoorStationCreate(BaseModel):
    extension_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    manufacturer: str | None = Field(None, max_length=100)
    model_name: str | None = Field(None, max_length=100)
    unlock_url: str | None = Field(None, max_length=500)
    unlock_http_method: str = Field("POST", pattern="^(GET|POST|PUT)$")
    unlock_headers: dict | None = None
    unlock_body: str | None = None
    unlock_dtmf_key: str | None = Field("#", max_length=5)
    ring_dest_type: str | None = Field(None, max_length=50)
    ring_dest_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None


class DoorStationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    manufacturer: str | None = Field(None, max_length=100)
    model_name: str | None = Field(None, max_length=100)
    unlock_url: str | None = Field(None, max_length=500)
    unlock_http_method: str | None = Field(None, pattern="^(GET|POST|PUT)$")
    unlock_headers: dict | None = None
    unlock_body: str | None = None
    unlock_dtmf_key: str | None = Field(None, max_length=5)
    ring_dest_type: str | None = None
    ring_dest_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    is_active: bool | None = None


class DoorStationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_id: uuid.UUID
    name: str
    description: str | None
    manufacturer: str | None
    model_name: str | None
    unlock_url: str | None
    unlock_http_method: str
    unlock_headers: dict | None
    unlock_body: str | None
    unlock_dtmf_key: str | None
    ring_dest_type: str | None
    ring_dest_id: uuid.UUID | None
    site_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DoorAccessLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    door_station_id: uuid.UUID
    caller_extension_id: uuid.UUID | None
    answered_by_extension_id: uuid.UUID | None
    door_unlocked: bool
    unlocked_by_user_id: uuid.UUID | None
    cdr_id: uuid.UUID | None
    call_started_at: datetime | None
    call_ended_at: datetime | None
    unlock_triggered_at: datetime | None
    created_at: datetime
