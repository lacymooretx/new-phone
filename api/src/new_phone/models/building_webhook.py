import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class WebhookActionType(StrEnum):
    PANIC_ALERT = "panic_alert"
    PAGE_ZONE = "page_zone"
    PAGE_ALL = "page_all"
    NOTIFICATION = "notification"


class BuildingWebhook(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "building_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_token: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    actions = relationship(
        "BuildingWebhookAction",
        back_populates="webhook",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "BuildingWebhookLog",
        back_populates="webhook",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class BuildingWebhookAction(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "building_webhook_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("building_webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type_match: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    action_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    webhook = relationship("BuildingWebhook", back_populates="actions")


class BuildingWebhookLog(Base):
    """Immutable log of received webhook events."""

    __tablename__ = "building_webhook_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("building_webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actions_taken: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    webhook = relationship("BuildingWebhook", back_populates="logs")
