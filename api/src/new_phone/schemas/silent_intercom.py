import uuid
from datetime import datetime

from pydantic import BaseModel


class SilentIntercomStartRequest(BaseModel):
    target_extension_id: uuid.UUID


class SilentIntercomResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    initiated_by_user_id: uuid.UUID
    target_extension_id: uuid.UUID
    fs_uuid: str | None
    status: str
    max_duration_seconds: int
    started_at: datetime
    ended_at: datetime | None
    ended_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
