import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.caller_id_rule import RuleAction, RuleType


class CallerIdRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rule_type: RuleType
    match_pattern: str = Field(..., min_length=1, max_length=40)
    action: RuleAction
    destination_id: uuid.UUID | None = None
    priority: int = Field(0, ge=0, le=9999)
    notes: str | None = None


class CallerIdRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    rule_type: RuleType | None = None
    match_pattern: str | None = Field(None, min_length=1, max_length=40)
    action: RuleAction | None = None
    destination_id: uuid.UUID | None = None
    priority: int | None = Field(None, ge=0, le=9999)
    notes: str | None = None


class CallerIdRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    rule_type: str
    match_pattern: str
    action: str
    destination_id: uuid.UUID | None
    priority: int
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
