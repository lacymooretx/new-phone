import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TelephonyProviderConfigCreate(BaseModel):
    provider_type: Literal["clearlyip", "twilio"]
    label: str = Field(..., min_length=1, max_length=100)
    credentials: dict
    is_default: bool = False
    notes: str | None = None


class TelephonyProviderConfigUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    credentials: dict | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class TelephonyProviderConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    provider_type: str
    label: str
    is_default: bool
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # encrypted_credentials is NEVER returned


class TelephonyProviderEffective(BaseModel):
    provider_type: str
    source: Literal["tenant", "msp", "env_var", "none"]
    is_configured: bool
    label: str | None = None
    config_id: uuid.UUID | None = None
