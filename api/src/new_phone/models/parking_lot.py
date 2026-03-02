import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class ParkingLot(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "parking_lots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "lot_number", name="uq_parking_lots_tenant_lot_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_start: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_end: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    comeback_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comeback_extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    moh_prompt = relationship("AudioPrompt", foreign_keys=[moh_prompt_id], lazy="joined")
    site = relationship("Site", foreign_keys=[site_id], lazy="joined")
