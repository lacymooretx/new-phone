import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class BossAdminCreate(BaseModel):
    executive_extension_id: uuid.UUID
    assistant_extension_id: uuid.UUID
    filter_mode: str = Field("all_to_assistant", max_length=30)
    overflow_ring_time: int = Field(20, ge=5, le=120)
    dnd_override_enabled: bool = False
    vip_caller_ids: list[str] = Field(default_factory=list)


class BossAdminUpdate(BaseModel):
    filter_mode: str | None = Field(None, max_length=30)
    overflow_ring_time: int | None = Field(None, ge=5, le=120)
    dnd_override_enabled: bool | None = None
    vip_caller_ids: list[str] | None = None
    is_active: bool | None = None


class BossAdminResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    executive_extension_id: uuid.UUID
    assistant_extension_id: uuid.UUID
    filter_mode: str
    overflow_ring_time: int
    dnd_override_enabled: bool
    vip_caller_ids: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    executive_extension_number: str | None = None
    assistant_extension_number: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _extract_extension_numbers(cls, data: object) -> object:
        if hasattr(data, "executive_extension") and data.executive_extension is not None:
            data.executive_extension_number = data.executive_extension.extension_number
        if hasattr(data, "assistant_extension") and data.assistant_extension is not None:
            data.assistant_extension_number = data.assistant_extension.extension_number
        return data


class BossAdminStatusView(BaseModel):
    executive_extension_id: uuid.UUID
    executive_extension_number: str
    executive_name: str | None = None
    current_call_status: str | None = None
