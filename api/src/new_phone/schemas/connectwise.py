"""Pydantic schemas for ConnectWise PSA integration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CWConfigCreate(BaseModel):
    company_id: str = Field(..., min_length=1, max_length=100)
    public_key: str = Field(..., min_length=1)
    private_key: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1, max_length=255)
    base_url: str = Field("https://na.myconnectwise.net", max_length=500)
    api_version: str = Field("2025.1", max_length=20)
    default_board_id: int | None = None
    default_status_id: int | None = None
    default_type_id: int | None = None
    auto_ticket_missed_calls: bool = True
    auto_ticket_voicemails: bool = True
    auto_ticket_completed_calls: bool = False
    min_call_duration_seconds: int = Field(0, ge=0)


class CWConfigUpdate(BaseModel):
    company_id: str | None = Field(None, min_length=1, max_length=100)
    public_key: str | None = None
    private_key: str | None = None
    client_id: str | None = Field(None, min_length=1, max_length=255)
    base_url: str | None = Field(None, max_length=500)
    api_version: str | None = Field(None, max_length=20)
    default_board_id: int | None = None
    default_status_id: int | None = None
    default_type_id: int | None = None
    auto_ticket_missed_calls: bool | None = None
    auto_ticket_voicemails: bool | None = None
    auto_ticket_completed_calls: bool | None = None
    min_call_duration_seconds: int | None = Field(None, ge=0)
    is_active: bool | None = None


class CWConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    company_id: str
    client_id: str
    base_url: str
    api_version: str
    default_board_id: int | None
    default_status_id: int | None
    default_type_id: int | None
    auto_ticket_missed_calls: bool
    auto_ticket_voicemails: bool
    auto_ticket_completed_calls: bool
    min_call_duration_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CWCompanyMappingCreate(BaseModel):
    cw_company_id: int = Field(..., ge=1)
    cw_company_name: str = Field(..., min_length=1, max_length=255)
    extension_id: uuid.UUID | None = None
    did_id: uuid.UUID | None = None


class CWCompanyMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    cw_config_id: uuid.UUID
    cw_company_id: int
    cw_company_name: str
    extension_id: uuid.UUID | None
    did_id: uuid.UUID | None


class CWTicketLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    cw_config_id: uuid.UUID
    cdr_id: uuid.UUID | None
    cw_ticket_id: int
    cw_company_id: int | None
    trigger_type: str
    ticket_summary: str
    status: str
    error_message: str | None
    created_at: datetime


class CWBoardResponse(BaseModel):
    id: int
    name: str


class CWStatusResponse(BaseModel):
    id: int
    name: str


class CWTypeResponse(BaseModel):
    id: int
    name: str


class CWCompanySearchResponse(BaseModel):
    id: int
    name: str
    identifier: str


class CWTestResponse(BaseModel):
    success: bool
    message: str


class CWTicketLogStats(BaseModel):
    today: int
    this_week: int
    this_month: int
    total: int
