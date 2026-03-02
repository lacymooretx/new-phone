import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.voicemail_box import GreetingType


class VoicemailBoxCreate(BaseModel):
    mailbox_number: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=20)
    greeting_type: GreetingType = GreetingType.DEFAULT
    email_notification: bool = True
    notification_email: str | None = Field(None, max_length=320)
    max_messages: int = Field(100, ge=1, le=9999)


class VoicemailBoxUpdate(BaseModel):
    mailbox_number: str | None = Field(None, min_length=1, max_length=20)
    greeting_type: GreetingType | None = None
    email_notification: bool | None = None
    notification_email: str | None = Field(None, max_length=320)
    max_messages: int | None = Field(None, ge=1, le=9999)


class VoicemailBoxResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    mailbox_number: str
    greeting_type: str
    email_notification: bool
    notification_email: str | None
    max_messages: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PinResetResponse(BaseModel):
    pin: str
