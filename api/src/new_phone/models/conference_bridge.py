import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class ConferenceBridge(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "conference_bridges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    participant_pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    moderator_pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    wait_for_moderator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    announce_join_leave: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    record_conference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    muted_on_join: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    moh_prompt = relationship("AudioPrompt", foreign_keys=[moh_prompt_id], lazy="joined")
