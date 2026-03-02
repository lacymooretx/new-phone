import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class CallFilterMode(StrEnum):
    ALL_TO_ASSISTANT = "all_to_assistant"
    SIMULTANEOUS_RING = "simultaneous_ring"
    ASSISTANT_OVERFLOW = "assistant_overflow"
    SCREENING = "screening"
    VIP_BYPASS = "vip_bypass"
    DND_OVERRIDE = "dnd_override"


class BossAdminStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BossAdminRelationship(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "boss_admin_relationships"
    __table_args__ = (
        UniqueConstraint(
            "executive_extension_id",
            "assistant_extension_id",
            name="uq_boss_admin_exec_asst",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    executive_extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assistant_extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filter_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="all_to_assistant"
    )
    overflow_ring_time: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    dnd_override_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    vip_caller_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    executive_extension = relationship(
        "Extension", foreign_keys=[executive_extension_id], lazy="joined"
    )
    assistant_extension = relationship(
        "Extension", foreign_keys=[assistant_extension_id], lazy="joined"
    )
