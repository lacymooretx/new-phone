import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ParkingLotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    lot_number: int = Field(..., ge=1)
    slot_start: int = Field(..., ge=1)
    slot_end: int = Field(..., ge=1)
    timeout_seconds: int = Field(60, ge=10, le=600)
    comeback_enabled: bool = True
    comeback_extension: str | None = Field(None, max_length=50)
    moh_prompt_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_slot_range(self):
        if self.slot_start > self.slot_end:
            raise ValueError("slot_start must be <= slot_end")
        return self


class ParkingLotUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    lot_number: int | None = Field(None, ge=1)
    slot_start: int | None = Field(None, ge=1)
    slot_end: int | None = Field(None, ge=1)
    timeout_seconds: int | None = Field(None, ge=10, le=600)
    comeback_enabled: bool | None = None
    comeback_extension: str | None = Field(None, max_length=50)
    moh_prompt_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None


class ParkingLotResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    lot_number: int
    slot_start: int
    slot_end: int
    timeout_seconds: int
    comeback_enabled: bool
    comeback_extension: str | None
    moh_prompt_id: uuid.UUID | None
    site_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SlotState(BaseModel):
    slot_number: int
    occupied: bool
    caller_id_number: str | None = None
    caller_id_name: str | None = None
    parked_at: str | None = None
    parked_by: str | None = None
    lot_name: str | None = None
    lot_id: str | None = None
