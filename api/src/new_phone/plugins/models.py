import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PluginStatus(StrEnum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PluginHookType(StrEnum):
    PRE_CALL = "pre_call"
    POST_CALL = "post_call"
    CDR_CREATED = "cdr_created"
    SMS_RECEIVED = "sms_received"
    SMS_SENT = "sms_sent"
    RECORDING_READY = "recording_ready"
    VOICEMAIL_RECEIVED = "voicemail_received"
    QUEUE_EVENT = "queue_event"


class Plugin(Base, TimestampMixin):
    __tablename__ = "plugins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    hook_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    tenant_plugins = relationship("TenantPlugin", back_populates="plugin", lazy="selectin")


class TenantPlugin(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "tenant_plugins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PluginStatus.INSTALLED)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    installed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    plugin = relationship("Plugin", back_populates="tenant_plugins", lazy="joined")
    tenant = relationship("Tenant", lazy="joined")


class PluginEventLog(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "plugin_event_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hook_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    plugin = relationship("Plugin", lazy="joined")
