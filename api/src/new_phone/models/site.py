import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class Site(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/New_York")
    address_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    outbound_cid_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outbound_cid_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audio_prompts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    moh_prompt = relationship("AudioPrompt", foreign_keys=[moh_prompt_id], lazy="joined")
