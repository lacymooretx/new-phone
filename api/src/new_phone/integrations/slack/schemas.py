"""Pydantic schemas for Slack integration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SlackConfigCreate(BaseModel):
    bot_token: str = Field(..., min_length=1)
    default_channel_id: str | None = Field(None, max_length=255)
    notify_missed_calls: bool = True
    notify_voicemails: bool = True
    notify_queue_alerts: bool = False


class SlackConfigUpdate(BaseModel):
    bot_token: str | None = None
    default_channel_id: str | None = Field(None, max_length=255)
    notify_missed_calls: bool | None = None
    notify_voicemails: bool | None = None
    notify_queue_alerts: bool | None = None
    is_active: bool | None = None


class SlackConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    default_channel_id: str | None
    notify_missed_calls: bool
    notify_voicemails: bool
    notify_queue_alerts: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SlackTestResponse(BaseModel):
    success: bool
    message: str
