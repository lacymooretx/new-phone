import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from new_phone.models.port_request import PortRequestProvider, PortRequestStatus


class PortRequestCreate(BaseModel):
    numbers: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of E.164 phone numbers to port",
    )
    current_carrier: str = Field(..., min_length=1, max_length=255)
    provider: PortRequestProvider
    requested_port_date: date | None = None
    notes: str | None = Field(None, max_length=2000)


class PortRequestUpdate(BaseModel):
    current_carrier: str | None = Field(None, min_length=1, max_length=255)
    requested_port_date: date | None = None
    notes: str | None = Field(None, max_length=2000)
    status: PortRequestStatus | None = None
    foc_date: date | None = None
    rejection_reason: str | None = Field(None, max_length=2000)


class PortRequestHistoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    port_request_id: uuid.UUID
    previous_status: str | None
    new_status: str
    changed_by: uuid.UUID | None
    notes: str | None
    created_at: datetime


class PortRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    numbers: list[str]
    current_carrier: str
    status: str
    provider: str
    provider_port_id: str | None
    loa_file_path: str | None
    foc_date: date | None
    requested_port_date: date | None
    actual_port_date: date | None
    rejection_reason: str | None
    notes: str | None
    submitted_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    history: list[PortRequestHistoryResponse] = []
