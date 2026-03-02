import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.building_webhook import WebhookActionType


class BuildingWebhookActionCreate(BaseModel):
    event_type_match: str = Field(..., min_length=1, max_length=100)
    action_type: WebhookActionType
    action_config: dict
    priority: int = Field(0, ge=0)
    is_active: bool = True


class BuildingWebhookActionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    webhook_id: uuid.UUID
    event_type_match: str
    action_type: str
    action_config: dict
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BuildingWebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class BuildingWebhookUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class BuildingWebhookResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    secret_token: str
    is_active: bool
    actions: list[BuildingWebhookActionResponse] = []
    created_at: datetime
    updated_at: datetime


class BuildingWebhookLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    webhook_id: uuid.UUID
    received_at: datetime
    source_ip: str
    payload: dict
    event_type: str | None
    actions_taken: dict | None
    status: str
    error_message: str | None
    created_at: datetime
