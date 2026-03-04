"""Pydantic schemas for Microsoft Teams integration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# -- TeamsConfig ---------------------------------------------------------------


class TeamsConfigCreate(BaseModel):
    azure_tenant_id: str = Field(..., max_length=255)
    client_id: str = Field(..., max_length=255)
    client_secret: str = Field(..., min_length=1, description="Will be encrypted at rest")
    presence_sync_enabled: bool = False
    direct_routing_enabled: bool = False
    bot_app_id: str | None = Field(None, max_length=255)


class TeamsConfigUpdate(BaseModel):
    azure_tenant_id: str | None = Field(None, max_length=255)
    client_id: str | None = Field(None, max_length=255)
    client_secret: str | None = Field(None, min_length=1)
    presence_sync_enabled: bool | None = None
    direct_routing_enabled: bool | None = None
    bot_app_id: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class TeamsConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    azure_tenant_id: str
    client_id: str
    presence_sync_enabled: bool
    direct_routing_enabled: bool
    bot_app_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# -- TeamsPresenceMapping ------------------------------------------------------


class TeamsPresenceMappingCreate(BaseModel):
    extension_id: uuid.UUID
    teams_user_id: str = Field(..., max_length=255)


class TeamsPresenceMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_id: uuid.UUID
    teams_user_id: str
    last_pbx_status: str | None
    last_teams_status: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


# -- Presence sync -------------------------------------------------------------


class TeamsPresenceSyncResponse(BaseModel):
    synced: int
    errors: int
    message: str
