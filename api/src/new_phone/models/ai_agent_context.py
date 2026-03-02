import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class AIAgentContext(Base, TimestampMixin):
    __tablename__ = "ai_agent_contexts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    greeting: Mapped[str] = mapped_column(Text, nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    monolithic_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline_stt: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline_llm: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline_tts: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline_options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en-US")
    barge_in_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    barge_in_sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, server_default="normal")
    silence_timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5000")
    max_call_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1800")
    available_tools: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    escalation_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    knowledge_base: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
    conversations = relationship("AIAgentConversation", back_populates="context", lazy="selectin")
