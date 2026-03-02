import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class CDRDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CDRDisposition(StrEnum):
    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    VOICEMAIL = "voicemail"
    CANCELLED = "cancelled"


class CDRResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    call_id: str
    direction: str
    caller_number: str
    caller_name: str
    called_number: str
    extension_id: uuid.UUID | None
    did_id: uuid.UUID | None
    trunk_id: uuid.UUID | None
    ring_group_id: uuid.UUID | None
    queue_id: uuid.UUID | None = None
    disposition: str
    hangup_cause: str | None
    duration_seconds: int
    billable_seconds: int
    ring_seconds: int
    start_time: datetime
    answer_time: datetime | None
    end_time: datetime
    has_recording: bool
    created_at: datetime
    agent_disposition_code_id: uuid.UUID | None = None
    agent_disposition_notes: str | None = None
    disposition_entered_at: datetime | None = None
    agent_disposition_label: str | None = None
    connectwise_ticket_id: int | None = None
    answered_by_extension_id: uuid.UUID | None = None
    on_behalf_of_extension_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    crm_customer_name: str | None = None
    crm_company_name: str | None = None
    crm_account_number: str | None = None
    crm_account_status: str | None = None
    crm_contact_id: str | None = None
    crm_provider_type: str | None = None
    crm_deep_link_url: str | None = None
    crm_custom_fields: dict | None = None
    crm_matched_at: datetime | None = None
    compliance_score: float | None = None
    compliance_evaluation_id: uuid.UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def _extract_disposition_label(cls, data: object) -> object:
        """Pull label from joined agent_disposition_code relationship."""
        if hasattr(data, "agent_disposition_code") and data.agent_disposition_code is not None:
            data.agent_disposition_label = data.agent_disposition_code.label  # type: ignore[union-attr]
        return data


class CDRDispositionUpdate(BaseModel):
    disposition_code_id: uuid.UUID
    notes: str | None = None


class CDRFilter(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    extension_id: uuid.UUID | None = None
    direction: CDRDirection | None = None
    disposition: CDRDisposition | None = None
    agent_disposition_code_id: uuid.UUID | None = None
    queue_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    crm_customer_name: str | None = None
    crm_company_name: str | None = None
    crm_account_number: str | None = None
    crm_matched: bool | None = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)
