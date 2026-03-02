import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class AIAgentToolDefinition(Base, TimestampMixin):
    __tablename__ = "ai_agent_tool_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    parameters_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_method: Mapped[str] = mapped_column(String(10), nullable=False, server_default="POST")
    webhook_headers_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    mcp_server_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_execution_time: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
