"""Pydantic schemas for CRM enrichment integration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.crm_config import CRMProviderType


class CRMConfigCreate(BaseModel):
    provider_type: CRMProviderType
    credentials: dict = Field(..., description="Provider-specific credentials blob")
    base_url: str | None = Field(None, max_length=500)
    cache_ttl_seconds: int = Field(3600, ge=60, le=86400)
    lookup_timeout_seconds: int = Field(5, ge=1, le=30)
    enrichment_enabled: bool = True
    enrich_inbound: bool = True
    enrich_outbound: bool = True
    custom_fields_map: dict | None = None


class CRMConfigUpdate(BaseModel):
    provider_type: CRMProviderType | None = None
    credentials: dict | None = None
    base_url: str | None = Field(None, max_length=500)
    cache_ttl_seconds: int | None = Field(None, ge=60, le=86400)
    lookup_timeout_seconds: int | None = Field(None, ge=1, le=30)
    enrichment_enabled: bool | None = None
    enrich_inbound: bool | None = None
    enrich_outbound: bool | None = None
    custom_fields_map: dict | None = None
    is_active: bool | None = None


class CRMConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: str
    base_url: str | None
    cache_ttl_seconds: int
    lookup_timeout_seconds: int
    enrichment_enabled: bool
    enrich_inbound: bool
    enrich_outbound: bool
    custom_fields_map: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CRMTestResponse(BaseModel):
    success: bool
    message: str


class CRMCacheInvalidateRequest(BaseModel):
    phone_number: str | None = Field(
        None, description="Specific phone number to invalidate. If omitted, invalidates all."
    )


class CRMCacheInvalidateResponse(BaseModel):
    keys_deleted: int
