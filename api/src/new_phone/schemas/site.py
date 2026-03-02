import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    timezone: str = "America/New_York"
    address_street: str | None = Field(None, max_length=255)
    address_city: str | None = Field(None, max_length=100)
    address_state: str | None = Field(None, max_length=50)
    address_zip: str | None = Field(None, max_length=20)
    address_country: str = Field("US", max_length=2)
    outbound_cid_name: str | None = Field(None, max_length=100)
    outbound_cid_number: str | None = Field(None, max_length=20)
    moh_prompt_id: uuid.UUID | None = None


class SiteUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    timezone: str | None = None
    address_street: str | None = Field(None, max_length=255)
    address_city: str | None = Field(None, max_length=100)
    address_state: str | None = Field(None, max_length=50)
    address_zip: str | None = Field(None, max_length=20)
    address_country: str | None = Field(None, max_length=2)
    outbound_cid_name: str | None = Field(None, max_length=100)
    outbound_cid_number: str | None = Field(None, max_length=20)
    moh_prompt_id: uuid.UUID | None = None


class SiteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    timezone: str
    address_street: str | None
    address_city: str | None
    address_state: str | None
    address_zip: str | None
    address_country: str
    outbound_cid_name: str | None
    outbound_cid_number: str | None
    moh_prompt_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SiteSummaryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    timezone: str
