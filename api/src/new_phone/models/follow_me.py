import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class FollowMeStrategy(StrEnum):
    SEQUENTIAL = "sequential"
    RING_ALL_EXTERNAL = "ring_all_external"


class FollowMe(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "follow_me"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    strategy: Mapped[str] = mapped_column(
        String(30), nullable=False, default=FollowMeStrategy.SEQUENTIAL
    )
    ring_extension_first: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extension_ring_time: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    destinations = relationship(
        "FollowMeDestination",
        back_populates="follow_me",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="FollowMeDestination.position",
    )


class FollowMeDestination(Base):
    __tablename__ = "follow_me_destinations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follow_me_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("follow_me.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    destination: Mapped[str] = mapped_column(String(40), nullable=False)
    ring_time: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    follow_me = relationship("FollowMe", back_populates="destinations")
