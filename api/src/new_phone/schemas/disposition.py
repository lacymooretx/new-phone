import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Disposition Codes ──


class DispositionCodeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    category: str | None = Field(None, max_length=50)
    position: int = Field(0, ge=0, le=1000)


class DispositionCodeUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=50)
    label: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = Field(None, max_length=50)
    position: int | None = Field(None, ge=0, le=1000)
    is_active: bool | None = None


class DispositionCodeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    list_id: uuid.UUID
    code: str
    label: str
    category: str | None
    position: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Disposition Code Lists ──


class DispositionCodeListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class DispositionCodeListUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class DispositionCodeListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    codes: list[DispositionCodeResponse] = []
    created_at: datetime
    updated_at: datetime
