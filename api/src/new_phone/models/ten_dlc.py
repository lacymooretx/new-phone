import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class Brand(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ten_dlc_brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ein: Mapped[str] = mapped_column(String(20), nullable=False)
    ein_issuing_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    brand_type: Mapped[str] = mapped_column(String(20), nullable=False)
    vertical: Mapped[str] = mapped_column(String(50), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    provider_brand_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
    campaigns = relationship("Campaign", back_populates="brand", lazy="selectin")
    compliance_docs = relationship("ComplianceDocument", back_populates="brand", lazy="selectin")


class Campaign(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ten_dlc_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ten_dlc_brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    use_case: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sample_messages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    message_flow: Mapped[str] = mapped_column(Text, nullable=False)
    help_message: Mapped[str] = mapped_column(String(500), nullable=False)
    opt_out_message: Mapped[str] = mapped_column(String(500), nullable=False)
    opt_in_keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="START")
    opt_out_keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="STOP")
    help_keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="HELP")
    number_pool: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    provider_campaign_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
    brand = relationship("Brand", back_populates="campaigns", lazy="joined")


class ComplianceDocument(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ten_dlc_compliance_docs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ten_dlc_brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
    brand = relationship("Brand", back_populates="compliance_docs", lazy="joined")
