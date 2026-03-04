import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class TeamsConfig(Base, TimestampMixin):
    __tablename__ = "teams_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    azure_tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_client_secret: Mapped[str] = mapped_column(Text, nullable=False)
    presence_sync_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    direct_routing_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    bot_app_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    tenant = relationship("Tenant", lazy="joined")
    presence_mappings = relationship(
        "TeamsPresenceMapping", back_populates="config", cascade="all, delete-orphan"
    )


class TeamsPresenceMapping(Base, TimestampMixin):
    __tablename__ = "teams_presence_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "extension_id", name="uq_teams_presence_ext"),
        UniqueConstraint("tenant_id", "teams_user_id", name="uq_teams_presence_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    teams_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    last_pbx_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_teams_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    config = relationship("TeamsConfig", back_populates="presence_mappings")
    extension = relationship("Extension", lazy="joined")
