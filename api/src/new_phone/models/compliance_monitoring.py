import uuid
from datetime import datetime

# ── Enums ──
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class ComplianceRuleCategory(StrEnum):
    GREETING = "greeting"
    DISCLOSURE = "disclosure"
    VERIFICATION = "verification"
    REQUIRED_STATEMENT = "required_statement"
    PROHIBITED_LANGUAGE = "prohibited_language"
    CLOSING = "closing"
    CUSTOM = "custom"


class ComplianceRuleSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ComplianceRuleScopeType(StrEnum):
    ALL = "all"
    QUEUE = "queue"
    AGENT_CONTEXT = "agent_context"


class ComplianceEvaluationStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWED = "reviewed"


class ComplianceRuleResultValue(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


# ── Models ──


class ComplianceRule(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "compliance_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default=ComplianceRuleCategory.CUSTOM)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default=ComplianceRuleSeverity.MAJOR)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ComplianceRuleScopeType.ALL)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")


class ComplianceEvaluation(Base, TenantScopedMixin):
    __tablename__ = "compliance_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cdr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_detail_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ai_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_agent_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rules_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_not_applicable: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ComplianceEvaluationStatus.PENDING
    )
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant = relationship("Tenant", lazy="joined")
    cdr = relationship("CallDetailRecord", foreign_keys=[cdr_id], lazy="joined")
    ai_conversation = relationship("AIAgentConversation", lazy="joined")
    reviewed_by = relationship("User", lazy="joined")
    rule_results = relationship(
        "ComplianceRuleResult",
        back_populates="evaluation",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ComplianceRuleResult(Base):
    __tablename__ = "compliance_rule_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evaluation = relationship("ComplianceEvaluation", back_populates="rule_results")
    rule = relationship("ComplianceRule", lazy="joined")
