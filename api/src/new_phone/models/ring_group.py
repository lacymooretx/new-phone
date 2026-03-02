import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class RingStrategy(StrEnum):
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    MEMORY_HUNT = "memory_hunt"


class RingGroup(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ring_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ring_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RingStrategy.SIMULTANEOUS
    )
    ring_time: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    ring_time_per_member: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    skip_busy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cid_passthrough: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confirm_calls: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Failover destination (polymorphic)
    failover_dest_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    failover_dest_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Music on Hold
    moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    moh_prompt = relationship("AudioPrompt", foreign_keys=[moh_prompt_id], lazy="joined")
    members = relationship(
        "RingGroupMember",
        back_populates="ring_group",
        order_by="RingGroupMember.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class RingGroupMember(Base):
    __tablename__ = "ring_group_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ring_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ring_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    ring_group = relationship("RingGroup", back_populates="members")
    extension = relationship("Extension", lazy="joined")
