import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OriginateRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=40)
    caller_extension_id: uuid.UUID | None = None
    originate_timeout: int = Field(30, ge=5, le=120)


class OriginateResponse(BaseModel):
    status: str
    destination: str
    caller_extension: str


class NumberHistoryEntry(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    direction: str
    caller_number: str
    caller_name: str
    called_number: str
    disposition: str
    duration_seconds: int
    start_time: datetime


class ExtensionLookupResponse(BaseModel):
    extension_id: uuid.UUID | None = None
    extension_number: str | None = None
    display_name: str | None = None
    dnd_enabled: bool = False
    agent_status: str | None = None
    is_internal: bool = False
