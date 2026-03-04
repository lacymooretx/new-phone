import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default=["read"])
    rate_limit: int = Field(default=1000, ge=1, le=100000)
    description: str | None = None
    expires_at: datetime | None = None


class ApiKeyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    scopes: list[str] | None = None
    rate_limit: int | None = Field(None, ge=1, le=100000)
    description: str | None = None
    is_active: bool | None = None


class ApiKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    rate_limit: int
    is_active: bool
    description: str | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only on creation — includes the full key (shown once)."""
    raw_key: str
