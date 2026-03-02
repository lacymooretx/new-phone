import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*$")
    domain: str | None = None
    sip_domain: str | None = None
    default_moh_prompt_id: uuid.UUID | None = None
    notes: str | None = None
    default_language: str = Field("en", max_length=10)


class TenantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*$")
    domain: str | None = None
    sip_domain: str | None = None
    default_moh_prompt_id: uuid.UUID | None = None
    notes: str | None = None
    is_active: bool | None = None
    default_language: str | None = Field(None, max_length=10)


class TenantResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    domain: str | None
    sip_domain: str | None
    default_moh_prompt_id: uuid.UUID | None = None
    is_active: bool
    notes: str | None
    default_language: str
    created_at: datetime
    updated_at: datetime
