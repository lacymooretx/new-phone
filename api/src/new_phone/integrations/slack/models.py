"""SQLAlchemy models for Slack integration configuration."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class SlackConfig(Base, TimestampMixin):
    __tablename__ = "slack_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    encrypted_bot_token: Mapped[str] = mapped_column(Text, nullable=False)
    default_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notify_missed_calls: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_voicemails: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_queue_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
