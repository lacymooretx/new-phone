import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class TrunkAuthType(StrEnum):
    REGISTRATION = "registration"
    IP_AUTH = "ip_auth"


class TrunkTransport(StrEnum):
    TLS = "tls"


class InboundCIDMode(StrEnum):
    PASSTHROUGH = "passthrough"
    REWRITE = "rewrite"
    BLOCK = "block"


class SIPTrunk(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sip_trunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=5061, nullable=False)

    # Registration credentials (encrypted)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_password: Mapped[str | None] = mapped_column(Text, nullable=True)

    # IP auth (comma-separated CIDR blocks)
    ip_acl: Mapped[str | None] = mapped_column(Text, nullable=True)

    codec_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_channels: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    transport: Mapped[str] = mapped_column(
        String(10), nullable=False, default=TrunkTransport.TLS
    )
    inbound_cid_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InboundCIDMode.PASSTHROUGH
    )

    # Failover
    failover_trunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sip_trunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    failover_trunk = relationship("SIPTrunk", remote_side="SIPTrunk.id", lazy="joined")
