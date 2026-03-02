import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PhoneModelCreate(BaseModel):
    manufacturer: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=50)
    model_family: str = Field(..., min_length=1, max_length=50)
    max_line_keys: int = Field(0, ge=0)
    max_expansion_keys: int = Field(0, ge=0)
    max_expansion_modules: int = Field(0, ge=0)
    has_color_screen: bool = False
    has_wifi: bool = False
    has_bluetooth: bool = False
    has_expansion_port: bool = False
    has_poe: bool = True
    has_gigabit: bool = False
    firmware_pattern: str | None = Field(None, max_length=100)
    notes: str | None = None


class PhoneModelUpdate(BaseModel):
    manufacturer: str | None = Field(None, min_length=1, max_length=50)
    model_name: str | None = Field(None, min_length=1, max_length=50)
    model_family: str | None = Field(None, min_length=1, max_length=50)
    max_line_keys: int | None = Field(None, ge=0)
    max_expansion_keys: int | None = Field(None, ge=0)
    max_expansion_modules: int | None = Field(None, ge=0)
    has_color_screen: bool | None = None
    has_wifi: bool | None = None
    has_bluetooth: bool | None = None
    has_expansion_port: bool | None = None
    has_poe: bool | None = None
    has_gigabit: bool | None = None
    firmware_pattern: str | None = Field(None, max_length=100)
    notes: str | None = None
    is_active: bool | None = None


class PhoneModelResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    manufacturer: str
    model_name: str
    model_family: str
    max_line_keys: int
    max_expansion_keys: int
    max_expansion_modules: int
    has_color_screen: bool
    has_wifi: bool
    has_bluetooth: bool
    has_expansion_port: bool
    has_poe: bool
    has_gigabit: bool
    firmware_pattern: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
