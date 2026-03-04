import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field

# --- Room schemas ---


class RoomCreate(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    extension_id: uuid.UUID | None = None
    floor: str | None = Field(None, max_length=10)
    room_type: str | None = Field(None, max_length=50)
    status: str = "vacant"
    housekeeping_status: str = "clean"
    guest_name: str | None = Field(None, max_length=100)
    guest_checkout_at: datetime | None = None
    wake_up_time: time | None = None
    wake_up_enabled: bool = False
    restricted_dialing: bool = True
    notes: str | None = None


class RoomUpdate(BaseModel):
    room_number: str | None = Field(None, min_length=1, max_length=20)
    extension_id: uuid.UUID | None = None
    floor: str | None = Field(None, max_length=10)
    room_type: str | None = Field(None, max_length=50)
    status: str | None = None
    housekeeping_status: str | None = None
    guest_name: str | None = Field(None, max_length=100)
    guest_checkout_at: datetime | None = None
    wake_up_time: time | None = None
    wake_up_enabled: bool | None = None
    restricted_dialing: bool | None = None
    notes: str | None = None


class RoomResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    room_number: str
    extension_id: uuid.UUID | None
    floor: str | None
    room_type: str | None
    status: str
    housekeeping_status: str
    guest_name: str | None
    guest_checkout_at: datetime | None
    wake_up_time: time | None
    wake_up_enabled: bool
    restricted_dialing: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RoomCheckIn(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=100)
    guest_checkout_at: datetime | None = None


# --- WakeUpCall schemas ---


class WakeUpCallCreate(BaseModel):
    scheduled_time: datetime


class WakeUpCallResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    room_id: uuid.UUID
    scheduled_time: datetime
    status: str
    attempt_count: int
    created_at: datetime
    updated_at: datetime
