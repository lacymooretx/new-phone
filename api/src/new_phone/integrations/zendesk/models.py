"""SQLAlchemy models for Zendesk integration configuration."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class ZendeskConfig(Base, TimestampMixin):
    __tablename__ = "zendesk_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    subdomain: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_api_token: Mapped[str] = mapped_column(Text, nullable=False)
    agent_email: Mapped[str] = mapped_column(String(320), nullable=False)
    auto_ticket_on_missed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    auto_ticket_on_voicemail: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
