"""Pydantic schemas for Zendesk integration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ZendeskConfigCreate(BaseModel):
    subdomain: str = Field(..., min_length=1, max_length=255)
    api_token: str = Field(..., min_length=1)
    agent_email: str = Field(..., min_length=1, max_length=320)
    auto_ticket_on_missed: bool = False
    auto_ticket_on_voicemail: bool = False


class ZendeskConfigUpdate(BaseModel):
    subdomain: str | None = Field(None, min_length=1, max_length=255)
    api_token: str | None = None
    agent_email: str | None = Field(None, min_length=1, max_length=320)
    auto_ticket_on_missed: bool | None = None
    auto_ticket_on_voicemail: bool | None = None
    is_active: bool | None = None


class ZendeskConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    subdomain: str
    agent_email: str
    auto_ticket_on_missed: bool
    auto_ticket_on_voicemail: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ZendeskTestResponse(BaseModel):
    success: bool
    message: str
