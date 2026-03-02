import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class IVRActionType(StrEnum):
    EXTENSION = "extension"
    RING_GROUP = "ring_group"
    VOICEMAIL = "voicemail"
    IVR = "ivr"
    TIME_CONDITION = "time_condition"
    QUEUE = "queue"
    CONFERENCE = "conference"
    EXTERNAL_TRANSFER = "external_transfer"
    HANGUP = "hangup"
    REPEAT = "repeat"


class IVRMenu(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ivr_menus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    greet_long_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    greet_short_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    invalid_sound_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    exit_sound_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_timeouts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    inter_digit_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    digit_len: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    exit_destination_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    exit_destination_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tts_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tts_voice: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
    greet_long_prompt = relationship("AudioPrompt", foreign_keys=[greet_long_prompt_id], lazy="joined")
    greet_short_prompt = relationship("AudioPrompt", foreign_keys=[greet_short_prompt_id], lazy="joined")
    invalid_sound_prompt = relationship("AudioPrompt", foreign_keys=[invalid_sound_prompt_id], lazy="joined")
    exit_sound_prompt = relationship("AudioPrompt", foreign_keys=[exit_sound_prompt_id], lazy="joined")
    options = relationship("IVRMenuOption", back_populates="ivr_menu", cascade="all, delete-orphan", lazy="selectin")


class IVRMenuOption(Base):
    __tablename__ = "ivr_menu_options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ivr_menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ivr_menus.id", ondelete="CASCADE"), nullable=False
    )
    digits: Mapped[str] = mapped_column(String(10), nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    action_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_target_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ivr_menu = relationship("IVRMenu", back_populates="options")
