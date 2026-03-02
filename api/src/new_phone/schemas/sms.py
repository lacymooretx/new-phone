import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.sms import ConversationState, SMSProvider

# ── SMS Provider Config ──────────────────────────────────────────────

class SMSProviderConfigCreate(BaseModel):
    provider_type: SMSProvider
    label: str = Field(..., min_length=1, max_length=100)
    credentials: dict
    is_default: bool = False
    notes: str | None = None


class SMSProviderConfigUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    credentials: dict | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class SMSProviderConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: str
    label: str
    is_default: bool
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ── Conversations ────────────────────────────────────────────────────

class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    did_id: uuid.UUID
    remote_number: str
    channel: str
    state: str
    assigned_to_user_id: uuid.UUID | None
    queue_id: uuid.UUID | None
    last_message_at: datetime | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed fields
    did_number: str | None = None
    assigned_to_name: str | None = None
    queue_name: str | None = None
    unread_count: int = 0
    last_message_preview: str | None = None


class ConversationUpdate(BaseModel):
    state: ConversationState | None = None
    assigned_to_user_id: uuid.UUID | None = None
    queue_id: uuid.UUID | None = None


# ── Messages ─────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1600)


class MessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    conversation_id: uuid.UUID
    direction: str
    from_number: str
    to_number: str
    body: str
    status: str
    provider: str | None
    provider_message_id: str | None
    sent_by_user_id: uuid.UUID | None
    error_message: str | None
    segments: int
    created_at: datetime
    # Computed
    sent_by_name: str | None = None


# ── Conversation Notes ───────────────────────────────────────────────

class ConversationNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class ConversationNoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    created_at: datetime
    # Computed
    user_name: str | None = None


# ── Opt-Outs ─────────────────────────────────────────────────────────

class OptOutResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    did_id: uuid.UUID
    phone_number: str
    reason: str
    is_opted_out: bool
    opted_out_at: datetime
    opted_in_at: datetime | None
