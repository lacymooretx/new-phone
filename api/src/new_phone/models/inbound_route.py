import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class InboundDestType(StrEnum):
    EXTENSION = "extension"
    RING_GROUP = "ring_group"
    VOICEMAIL = "voicemail"
    IVR = "ivr"
    TIME_CONDITION = "time_condition"
    QUEUE = "queue"
    CONFERENCE = "conference"
    EXTERNAL = "external"
    TERMINATE = "terminate"
    AI_AGENT = "ai_agent"


class InboundRoute(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "inbound_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    did_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dids.id", ondelete="SET NULL"),
        nullable=True,
    )
    destination_type: Mapped[str] = mapped_column(String(20), nullable=False)
    destination_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cid_name_prefix: Mapped[str | None] = mapped_column(String(50), nullable=True)
    time_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    did = relationship("DID", lazy="joined")
