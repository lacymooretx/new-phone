import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.queue import AgentStatus, QueueStrategy

# ── Queue Members ──


class QueueMemberCreate(BaseModel):
    extension_id: uuid.UUID
    level: int = Field(1, ge=1, le=100)
    position: int = Field(1, ge=1, le=100)


class QueueMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    queue_id: uuid.UUID
    extension_id: uuid.UUID
    level: int
    position: int


# ── Queue CRUD ──


class QueueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    queue_number: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    strategy: QueueStrategy = QueueStrategy.LONGEST_IDLE_AGENT
    moh_prompt_id: uuid.UUID | None = None
    max_wait_time: int = Field(300, ge=0, le=7200)
    max_wait_time_with_no_agent: int = Field(120, ge=0, le=7200)
    tier_rules_apply: bool = True
    tier_rule_wait_second: int = Field(300, ge=0, le=7200)
    tier_rule_wait_multiply_level: bool = True
    tier_rule_no_agent_no_wait: bool = False
    discard_abandoned_after: int = Field(60, ge=0, le=7200)
    abandoned_resume_allowed: bool = False
    caller_exit_key: str | None = Field(None, max_length=5)
    wrapup_time: int = Field(0, ge=0, le=600)
    ring_timeout: int = Field(30, ge=5, le=300)
    announce_frequency: int = Field(0, ge=0, le=600)
    announce_prompt_id: uuid.UUID | None = None
    overflow_destination_type: str | None = Field(None, max_length=20)
    overflow_destination_id: uuid.UUID | None = None
    record_calls: bool = False
    enabled: bool = True
    disposition_required: bool = False
    disposition_code_list_id: uuid.UUID | None = None
    members: list[QueueMemberCreate] = Field(default_factory=list)


class QueueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    queue_number: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    strategy: QueueStrategy | None = None
    moh_prompt_id: uuid.UUID | None = None
    max_wait_time: int | None = Field(None, ge=0, le=7200)
    max_wait_time_with_no_agent: int | None = Field(None, ge=0, le=7200)
    tier_rules_apply: bool | None = None
    tier_rule_wait_second: int | None = Field(None, ge=0, le=7200)
    tier_rule_wait_multiply_level: bool | None = None
    tier_rule_no_agent_no_wait: bool | None = None
    discard_abandoned_after: int | None = Field(None, ge=0, le=7200)
    abandoned_resume_allowed: bool | None = None
    caller_exit_key: str | None = Field(None, max_length=5)
    wrapup_time: int | None = Field(None, ge=0, le=600)
    ring_timeout: int | None = Field(None, ge=5, le=300)
    announce_frequency: int | None = Field(None, ge=0, le=600)
    announce_prompt_id: uuid.UUID | None = None
    overflow_destination_type: str | None = Field(None, max_length=20)
    overflow_destination_id: uuid.UUID | None = None
    record_calls: bool | None = None
    enabled: bool | None = None
    disposition_required: bool | None = None
    disposition_code_list_id: uuid.UUID | None = None
    members: list[QueueMemberCreate] | None = None


class QueueResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    queue_number: str
    description: str | None
    strategy: str
    moh_prompt_id: uuid.UUID | None
    max_wait_time: int
    max_wait_time_with_no_agent: int
    tier_rules_apply: bool
    tier_rule_wait_second: int
    tier_rule_wait_multiply_level: bool
    tier_rule_no_agent_no_wait: bool
    discard_abandoned_after: int
    abandoned_resume_allowed: bool
    caller_exit_key: str | None
    wrapup_time: int
    ring_timeout: int
    announce_frequency: int
    announce_prompt_id: uuid.UUID | None
    overflow_destination_type: str | None
    overflow_destination_id: uuid.UUID | None
    record_calls: bool
    enabled: bool
    disposition_required: bool
    disposition_code_list_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: list[QueueMemberResponse] = []


# ── Agent Status ──


class AgentStatusUpdate(BaseModel):
    status: AgentStatus


class AgentStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    extension_id: uuid.UUID
    extension_number: str
    agent_status: str | None


# ── Queue Stats ──


class QueueStatsResponse(BaseModel):
    queue_id: uuid.UUID
    queue_name: str
    waiting_count: int = 0
    agents_logged_in: int = 0
    agents_available: int = 0
    agents_on_call: int = 0
    longest_wait_seconds: int = 0
