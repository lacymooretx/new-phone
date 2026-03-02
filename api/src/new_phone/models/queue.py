import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class QueueStrategy(StrEnum):
    RING_ALL = "ring-all"
    LONGEST_IDLE_AGENT = "longest-idle-agent"
    ROUND_ROBIN = "round-robin"
    TOP_DOWN = "top-down"
    AGENT_WITH_LEAST_TALK_TIME = "agent-with-least-talk-time"
    AGENT_WITH_FEWEST_CALLS = "agent-with-fewest-calls"
    SEQUENTIALLY_BY_AGENT_ORDER = "sequentially-by-agent-order"
    RANDOM = "random"
    RING_PROGRESSIVELY = "ring-progressively"


class AgentStatus(StrEnum):
    AVAILABLE = "Available"
    LOGGED_OUT = "Logged Out"
    ON_BREAK = "On Break"


class Queue(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "queues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    queue_number: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, default=QueueStrategy.LONGEST_IDLE_AGENT)

    # Hold music
    moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )

    # Queue behavior
    max_wait_time: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    max_wait_time_with_no_agent: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    tier_rules_apply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tier_rule_wait_second: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    tier_rule_wait_multiply_level: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tier_rule_no_agent_no_wait: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discard_abandoned_after: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    abandoned_resume_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    caller_exit_key: Mapped[str | None] = mapped_column(String(5), nullable=True)
    wrapup_time: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ring_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Announcements
    announce_frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    announce_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )

    # Overflow routing
    overflow_destination_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    overflow_destination_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    record_calls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Disposition codes
    disposition_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disposition_code_list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disposition_code_lists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tenant = relationship("Tenant", lazy="joined")
    moh_prompt = relationship("AudioPrompt", foreign_keys=[moh_prompt_id], lazy="joined")
    announce_prompt = relationship("AudioPrompt", foreign_keys=[announce_prompt_id], lazy="joined")
    disposition_code_list = relationship("DispositionCodeList", lazy="joined")
    members = relationship(
        "QueueMember",
        back_populates="queue",
        order_by="QueueMember.level, QueueMember.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class QueueMember(Base):
    __tablename__ = "queue_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="CASCADE"),
        nullable=False,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    queue = relationship("Queue", back_populates="members")
    extension = relationship("Extension", lazy="joined")
