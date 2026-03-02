import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SSOProviderCreate(BaseModel):
    provider_type: str = Field(..., pattern="^(microsoft|google)$")
    display_name: str = Field(..., min_length=1, max_length=255)
    client_id: str = Field(..., min_length=1, max_length=255)
    client_secret: str = Field(..., min_length=1)
    issuer_url: str = Field(..., min_length=1, max_length=500)
    scopes: str = Field("openid email profile", max_length=500)
    auto_provision: bool = True
    default_role: str = Field("tenant_user", max_length=30)
    enforce_sso: bool = False


class SSOProviderUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    client_id: str | None = Field(None, min_length=1, max_length=255)
    client_secret: str | None = None
    issuer_url: str | None = Field(None, min_length=1, max_length=500)
    scopes: str | None = Field(None, max_length=500)
    auto_provision: bool | None = None
    default_role: str | None = Field(None, max_length=30)
    enforce_sso: bool | None = None
    is_active: bool | None = None


class SSOProviderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: str
    display_name: str
    client_id: str
    issuer_url: str
    discovery_url: str
    scopes: str
    auto_provision: bool
    default_role: str
    enforce_sso: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SSORoleMappingCreate(BaseModel):
    external_group_id: str = Field(..., min_length=1, max_length=255)
    external_group_name: str | None = Field(None, max_length=255)
    pbx_role: str = Field(..., pattern="^(tenant_admin|tenant_manager|tenant_user)$")


class SSORoleMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    external_group_id: str
    external_group_name: str | None
    pbx_role: str


class SSOTestResponse(BaseModel):
    success: bool
    message: str
