import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin

# ── Enums ──


class AttestationLevel(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class SpamAction(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    CHALLENGE = "challenge"


# ── Models ──


class StirShakenConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "stir_shaken_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_stir_shaken_configs_tenant"),
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
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certificate_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_key_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_attestation: Mapped[str] = mapped_column(
        String(1), nullable=False, default=AttestationLevel.A
    )
    verify_inbound: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")


class SpamFilter(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "spam_filters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_attestation: Mapped[str | None] = mapped_column(String(1), nullable=True)
    spam_score_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SpamAction.BLOCK
    )

    tenant = relationship("Tenant", lazy="joined")


class SpamBlockList(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "spam_block_list"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "phone_number", name="uq_spam_block_list_tenant_phone"
        ),
        Index("ix_spam_block_list_phone_number", "phone_number"),
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
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    tenant = relationship("Tenant", lazy="joined")


class SpamAllowList(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "spam_allow_list"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "phone_number", name="uq_spam_allow_list_tenant_phone"
        ),
        Index("ix_spam_allow_list_phone_number", "phone_number"),
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
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
