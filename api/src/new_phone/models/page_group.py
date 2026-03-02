import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PageMode(StrEnum):
    ONE_WAY = "one_way"
    TWO_WAY = "two_way"


class PageGroup(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "page_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_mode: Mapped[str] = mapped_column(String(10), nullable=False, default=PageMode.ONE_WAY)
    timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    tenant = relationship("Tenant", lazy="joined")
    site = relationship("Site", lazy="joined")
    members = relationship(
        "PageGroupMember",
        back_populates="page_group",
        order_by="PageGroupMember.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PageGroupMember(Base):
    __tablename__ = "page_group_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("page_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    page_group = relationship("PageGroup", back_populates="members")
    extension = relationship("Extension", lazy="joined")
