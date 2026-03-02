import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConferenceBridgeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    room_number: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    max_participants: int = Field(50, ge=0, le=300)
    participant_pin: str | None = Field(None, max_length=20)
    moderator_pin: str | None = Field(None, max_length=20)
    wait_for_moderator: bool = False
    announce_join_leave: bool = True
    moh_prompt_id: uuid.UUID | None = None
    record_conference: bool = False
    muted_on_join: bool = False
    enabled: bool = True


class ConferenceBridgeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    room_number: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    max_participants: int | None = Field(None, ge=0, le=300)
    participant_pin: str | None = Field(None, max_length=20)
    moderator_pin: str | None = Field(None, max_length=20)
    wait_for_moderator: bool | None = None
    announce_join_leave: bool | None = None
    moh_prompt_id: uuid.UUID | None = None
    record_conference: bool | None = None
    muted_on_join: bool | None = None
    enabled: bool | None = None


class ConferenceBridgeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    room_number: str
    description: str | None
    max_participants: int
    participant_pin: str | None
    moderator_pin: str | None
    wait_for_moderator: bool
    announce_join_leave: bool
    moh_prompt_id: uuid.UUID | None
    record_conference: bool
    muted_on_join: bool
    enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
