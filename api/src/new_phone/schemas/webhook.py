import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_url: str = Field(min_length=1, max_length=2048)
    event_types: list[str] = Field(min_length=1)
    description: str | None = None
    is_active: bool = True


class WebhookSubscriptionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    target_url: str | None = Field(None, min_length=1, max_length=2048)
    event_types: list[str] | None = None
    description: str | None = None
    is_active: bool | None = None


class WebhookSubscriptionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    target_url: str
    event_types: list[str]
    is_active: bool
    description: str | None
    failure_count: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: str
    payload: dict
    status: str
    response_status_code: int | None
    response_body: str | None
    error_message: str | None
    attempt_count: int
    next_retry_at: datetime | None
    created_at: datetime


class WebhookTestRequest(BaseModel):
    event_type: str = "test.ping"
