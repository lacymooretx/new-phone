import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScheduledCallbackCreate(BaseModel):
    queue_id: uuid.UUID
    caller_number: str = Field(min_length=1, max_length=20)
    caller_name: str | None = Field(None, max_length=100)
    scheduled_at: datetime
    max_attempts: int = Field(default=3, ge=1, le=10)
    notes: str | None = None


class ScheduledCallbackUpdate(BaseModel):
    scheduled_at: datetime | None = None
    status: str | None = None
    notes: str | None = None


class ScheduledCallbackResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    queue_id: uuid.UUID
    caller_number: str
    caller_name: str | None
    scheduled_at: datetime
    status: str
    queue_position: int | None
    attempt_count: int
    max_attempts: int
    completed_at: datetime | None
    agent_extension: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
