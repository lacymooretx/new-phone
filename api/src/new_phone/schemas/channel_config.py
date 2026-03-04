import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.channel_config import ChannelType


class ChannelConfigCreate(BaseModel):
    channel_type: ChannelType
    display_name: str = Field(..., min_length=1, max_length=100)
    credentials: dict
    is_active: bool = True
    queue_id: uuid.UUID | None = None


class ChannelConfigUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    credentials: dict | None = None
    is_active: bool | None = None
    queue_id: uuid.UUID | None = None


class ChannelConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    channel_type: str
    display_name: str
    is_active: bool
    queue_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
