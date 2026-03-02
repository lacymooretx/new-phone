"""Pydantic schemas for AI Voice Agent system."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Provider Configs ─────────────────────────────────────────

class AIProviderConfigCreate(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    base_url: str | None = Field(None, max_length=500)
    model_id: str | None = Field(None, max_length=100)
    extra_config: dict | None = None


class AIProviderConfigUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = Field(None, max_length=500)
    model_id: str | None = Field(None, max_length=100)
    extra_config: dict | None = None
    is_active: bool | None = None


class AIProviderConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_name: str
    base_url: str | None
    model_id: str | None
    extra_config: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Agent Contexts ───────────────────────────────────────────

class AIAgentContextCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    system_prompt: str = Field(..., min_length=1)
    greeting: str = Field(..., min_length=1)
    provider_mode: str = Field(..., pattern="^(monolithic|pipeline)$")
    monolithic_provider: str | None = Field(None, max_length=50)
    pipeline_stt: str | None = Field(None, max_length=50)
    pipeline_llm: str | None = Field(None, max_length=50)
    pipeline_tts: str | None = Field(None, max_length=50)
    pipeline_options: dict | None = None
    voice_id: str | None = Field(None, max_length=100)
    language: str = Field("en-US", max_length=10)
    barge_in_enabled: bool = True
    barge_in_sensitivity: str = Field("normal", max_length=20)
    silence_timeout_ms: int = Field(5000, ge=1000, le=30000)
    max_call_duration_seconds: int = Field(1800, ge=60, le=7200)
    available_tools: list[str] | None = None
    escalation_rules: dict | None = None
    knowledge_base: str | None = None


class AIAgentContextUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    system_prompt: str | None = Field(None, min_length=1)
    greeting: str | None = Field(None, min_length=1)
    provider_mode: str | None = Field(None, pattern="^(monolithic|pipeline)$")
    monolithic_provider: str | None = Field(None, max_length=50)
    pipeline_stt: str | None = Field(None, max_length=50)
    pipeline_llm: str | None = Field(None, max_length=50)
    pipeline_tts: str | None = Field(None, max_length=50)
    pipeline_options: dict | None = None
    voice_id: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=10)
    barge_in_enabled: bool | None = None
    barge_in_sensitivity: str | None = Field(None, max_length=20)
    silence_timeout_ms: int | None = Field(None, ge=1000, le=30000)
    max_call_duration_seconds: int | None = Field(None, ge=60, le=7200)
    available_tools: list[str] | None = None
    escalation_rules: dict | None = None
    knowledge_base: str | None = None
    is_active: bool | None = None


class AIAgentContextResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    display_name: str
    system_prompt: str
    greeting: str
    provider_mode: str
    monolithic_provider: str | None
    pipeline_stt: str | None
    pipeline_llm: str | None
    pipeline_tts: str | None
    pipeline_options: dict | None
    voice_id: str | None
    language: str
    barge_in_enabled: bool
    barge_in_sensitivity: str
    silence_timeout_ms: int
    max_call_duration_seconds: int
    available_tools: list | None
    escalation_rules: dict | None
    knowledge_base: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Tool Definitions ─────────────────────────────────────────

class AIAgentToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: str = Field(..., pattern="^(webhook|mcp)$")
    parameters_schema: dict = Field(...)
    webhook_url: str | None = Field(None, max_length=500)
    webhook_method: str = Field("POST", max_length=10)
    webhook_headers: dict | None = None
    mcp_server_url: str | None = Field(None, max_length=500)
    max_execution_time: int = Field(30, ge=1, le=120)


class AIAgentToolUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    parameters_schema: dict | None = None
    webhook_url: str | None = Field(None, max_length=500)
    webhook_method: str | None = Field(None, max_length=10)
    webhook_headers: dict | None = None
    mcp_server_url: str | None = Field(None, max_length=500)
    max_execution_time: int | None = Field(None, ge=1, le=120)
    is_active: bool | None = None


class AIAgentToolResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    display_name: str
    description: str
    category: str
    parameters_schema: dict
    webhook_url: str | None
    webhook_method: str
    mcp_server_url: str | None
    max_execution_time: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Conversations ────────────────────────────────────────────

class AIAgentConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    context_id: uuid.UUID | None
    call_id: str
    caller_number: str
    caller_name: str | None
    provider_name: str
    outcome: str
    duration_seconds: int
    turn_count: int
    barge_in_count: int
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime


class AIAgentConversationDetail(AIAgentConversationResponse):
    transcript: list[dict]
    tool_calls: list[dict] | None
    summary: str | None
    transferred_to: str | None
    latency_metrics: dict | None
    provider_cost_usd: Decimal | None


# ── Stats ────────────────────────────────────────────────────

class AIAgentStatsResponse(BaseModel):
    calls_today: int = 0
    calls_this_week: int = 0
    calls_this_month: int = 0
    avg_duration_seconds: float = 0.0
    avg_turn_response_ms: float = 0.0
    transfer_rate: float = 0.0
    outcomes: dict[str, int] = {}


# ── Provider Status ──────────────────────────────────────────

class AIAgentProviderStatus(BaseModel):
    name: str
    display_name: str
    configured: bool
    status: str  # "connected", "error", "unconfigured"


# ── Call Control ─────────────────────────────────────────────

class AIAgentCallControl(BaseModel):
    call_id: str
    tenant_id: str
    context_name: str | None = None
    action: str | None = None  # "start" or "stop"


# ── Test ─────────────────────────────────────────────────────

class AIAgentTestRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class AIAgentTestResponse(BaseModel):
    success: bool
    response: str = ""
    provider: str = ""
    latency_ms: float = 0.0


class AIAgentProviderTestResponse(BaseModel):
    success: bool
    message: str
    provider: str


# ── Internal ESL ─────────────────────────────────────────────

class ESLTransferRequest(BaseModel):
    call_id: str
    tenant_id: str
    target: str


class ESLHangupRequest(BaseModel):
    call_id: str
    tenant_id: str


class ESLHoldRequest(BaseModel):
    call_id: str
    tenant_id: str
    hold: bool = True
