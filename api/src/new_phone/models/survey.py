import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class SurveyQuestionType(StrEnum):
    RATING = "rating"  # 1-5 DTMF
    YES_NO = "yes_no"  # 1=yes, 2=no
    NUMERIC = "numeric"  # Any DTMF digits


class SurveyTemplate(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "survey_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    intro_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    thank_you_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    responses = relationship("SurveyResponse", back_populates="template", lazy="selectin")


class SurveyResponse(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("survey_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    caller_number: Mapped[str] = mapped_column(String(20), nullable=False)
    call_uuid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template = relationship("SurveyTemplate", back_populates="responses")
    queue = relationship("Queue", lazy="joined")
