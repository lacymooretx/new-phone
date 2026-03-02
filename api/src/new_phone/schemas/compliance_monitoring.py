import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# ── Rule schemas ──


class ComplianceRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rule_text: str = Field(..., min_length=1)
    category: str = Field("custom", pattern=r"^(greeting|disclosure|verification|required_statement|prohibited_language|closing|custom)$")
    severity: str = Field("major", pattern=r"^(critical|major|minor)$")
    scope_type: str = Field("all", pattern=r"^(all|queue|agent_context)$")
    scope_id: uuid.UUID | None = None


class ComplianceRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    rule_text: str | None = Field(None, min_length=1)
    category: str | None = Field(None, pattern=r"^(greeting|disclosure|verification|required_statement|prohibited_language|closing|custom)$")
    severity: str | None = Field(None, pattern=r"^(critical|major|minor)$")
    scope_type: str | None = Field(None, pattern=r"^(all|queue|agent_context)$")
    scope_id: uuid.UUID | None = None
    is_active: bool | None = None


class ComplianceRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    rule_text: str
    category: str
    severity: str
    scope_type: str
    scope_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Evaluation schemas ──


class ComplianceEvaluationTrigger(BaseModel):
    cdr_id: uuid.UUID | None = None
    ai_conversation_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_exactly_one(self) -> "ComplianceEvaluationTrigger":
        if bool(self.cdr_id) == bool(self.ai_conversation_id):
            raise ValueError("Provide exactly one of cdr_id or ai_conversation_id")
        return self


class ComplianceRuleResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    evaluation_id: uuid.UUID
    rule_id: uuid.UUID | None
    rule_name_snapshot: str
    rule_text_snapshot: str
    result: str
    explanation: str | None
    evidence: str | None
    created_at: datetime


class ComplianceEvaluationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    cdr_id: uuid.UUID | None
    ai_conversation_id: uuid.UUID | None
    overall_score: float | None
    rules_passed: int
    rules_failed: int
    rules_not_applicable: int
    is_flagged: bool
    status: str
    provider_name: str | None
    reviewed_by_id: uuid.UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    evaluated_at: datetime | None
    created_at: datetime


class ComplianceEvaluationDetailResponse(ComplianceEvaluationResponse):
    transcript_text: str
    rule_results: list[ComplianceRuleResultResponse] = []


class ComplianceEvaluationReview(BaseModel):
    review_notes: str | None = None


# ── Analytics schemas ──


class ComplianceSummary(BaseModel):
    total_evaluations: int = 0
    average_score: float | None = None
    flagged_count: int = 0
    flagged_rate: float = 0.0
    pass_rate: float = 0.0
    status_breakdown: dict[str, int] = {}


class ComplianceAgentScore(BaseModel):
    extension_id: uuid.UUID
    extension_number: str
    evaluation_count: int = 0
    average_score: float | None = None
    flagged_count: int = 0


class ComplianceQueueScore(BaseModel):
    queue_id: uuid.UUID
    queue_name: str
    evaluation_count: int = 0
    average_score: float | None = None
    flagged_count: int = 0


class ComplianceRuleEffectiveness(BaseModel):
    rule_id: uuid.UUID
    rule_name: str
    severity: str
    total_evaluated: int = 0
    pass_count: int = 0
    fail_count: int = 0
    not_applicable_count: int = 0
    fail_rate: float = 0.0


class ComplianceTrendPoint(BaseModel):
    period: str
    evaluation_count: int = 0
    average_score: float | None = None
    flagged_count: int = 0
