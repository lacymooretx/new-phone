import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class AIAgentConversation(Base):
    __tablename__ = "ai_agent_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    context_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_agent_contexts.id", ondelete="SET NULL"),
        nullable=True,
    )
    call_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    cdr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_detail_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    caller_number: Mapped[str] = mapped_column(String(50), nullable=False)
    caller_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    transcript: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    transferred_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    barge_in_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    latency_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant = relationship("Tenant", lazy="joined")
    context = relationship("AIAgentContext", back_populates="conversations", lazy="joined")
    cdr = relationship("CallDetailRecord", lazy="joined")
