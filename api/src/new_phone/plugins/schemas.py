import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Plugin ────────────────────────────────────────────────────────────


class PluginCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=20)
    author: str = Field(min_length=1, max_length=100)
    description: str
    icon_url: str | None = None
    homepage_url: str | None = None
    manifest: dict = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    hook_types: list[str] = Field(default_factory=list)
    is_published: bool = False
    webhook_url: str | None = None


class PluginUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    version: str | None = Field(None, min_length=1, max_length=20)
    author: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    icon_url: str | None = None
    homepage_url: str | None = None
    manifest: dict | None = None
    permissions: list[str] | None = None
    hook_types: list[str] | None = None
    is_published: bool | None = None
    webhook_url: str | None = None


class PluginResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    version: str
    author: str
    description: str
    icon_url: str | None
    homepage_url: str | None
    manifest: dict
    permissions: list[str]
    hook_types: list[str]
    is_published: bool
    webhook_url: str | None
    created_at: datetime
    updated_at: datetime


# ── TenantPlugin ─────────────────────────────────────────────────────


class TenantPluginCreate(BaseModel):
    """Body is not needed; plugin_id comes from URL path."""


class TenantPluginConfigUpdate(BaseModel):
    config: dict


class TenantPluginResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    plugin_id: uuid.UUID
    status: str
    config: dict | None
    installed_at: datetime
    installed_by_user_id: uuid.UUID | None
    plugin: PluginResponse
    created_at: datetime
    updated_at: datetime


# ── PluginEventLog ───────────────────────────────────────────────────


class PluginEventLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    plugin_id: uuid.UUID
    hook_type: str
    payload: dict
    response_status: int | None
    error_message: str | None
    created_at: datetime
