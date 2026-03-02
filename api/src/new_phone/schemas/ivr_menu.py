import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IVRMenuOptionCreate(BaseModel):
    digits: str = Field(..., min_length=1, max_length=10)
    action_type: str
    action_target_id: uuid.UUID | None = None
    action_target_value: str | None = None
    label: str | None = None
    position: int = 0


class IVRMenuOptionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    ivr_menu_id: uuid.UUID
    digits: str
    action_type: str
    action_target_id: uuid.UUID | None
    action_target_value: str | None
    label: str | None
    position: int


class IVRMenuCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    greet_long_prompt_id: uuid.UUID | None = None
    greet_short_prompt_id: uuid.UUID | None = None
    invalid_sound_prompt_id: uuid.UUID | None = None
    exit_sound_prompt_id: uuid.UUID | None = None
    timeout: int = Field(10, ge=1, le=300)
    max_failures: int = Field(3, ge=1, le=10)
    max_timeouts: int = Field(3, ge=1, le=10)
    inter_digit_timeout: int = Field(2, ge=1, le=30)
    digit_len: int = Field(1, ge=1, le=10)
    exit_destination_type: str | None = None
    exit_destination_id: uuid.UUID | None = None
    enabled: bool = True
    options: list[IVRMenuOptionCreate] = Field(default_factory=list)


class IVRMenuUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    greet_long_prompt_id: uuid.UUID | None = None
    greet_short_prompt_id: uuid.UUID | None = None
    invalid_sound_prompt_id: uuid.UUID | None = None
    exit_sound_prompt_id: uuid.UUID | None = None
    timeout: int | None = Field(None, ge=1, le=300)
    max_failures: int | None = Field(None, ge=1, le=10)
    max_timeouts: int | None = Field(None, ge=1, le=10)
    inter_digit_timeout: int | None = Field(None, ge=1, le=30)
    digit_len: int | None = Field(None, ge=1, le=10)
    exit_destination_type: str | None = None
    exit_destination_id: uuid.UUID | None = None
    enabled: bool | None = None
    options: list[IVRMenuOptionCreate] | None = None


class IVRMenuResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    greet_long_prompt_id: uuid.UUID | None
    greet_short_prompt_id: uuid.UUID | None
    invalid_sound_prompt_id: uuid.UUID | None
    exit_sound_prompt_id: uuid.UUID | None
    timeout: int
    max_failures: int
    max_timeouts: int
    inter_digit_timeout: int
    digit_len: int
    exit_destination_type: str | None
    exit_destination_id: uuid.UUID | None
    tts_engine: str | None
    tts_voice: str | None
    enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    options: list[IVRMenuOptionResponse] = []
