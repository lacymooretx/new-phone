import uuid
from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin

# ── Enums ──


class DNCListType(StrEnum):
    INTERNAL = "internal"
    NATIONAL = "national"
    STATE = "state"
    CUSTOM = "custom"


class DNCEntrySource(StrEnum):
    MANUAL = "manual"
    API = "api"
    BULK_UPLOAD = "bulk_upload"
    SMS_SYNC = "sms_sync"
    CALLER_REQUEST = "caller_request"


class ConsentMethod(StrEnum):
    WEB_FORM = "web_form"
    VERBAL = "verbal"
    PAPER = "paper"
    SMS_KEYWORD = "sms_keyword"
    API = "api"


class CampaignType(StrEnum):
    MARKETING = "marketing"
    TRANSACTIONAL = "transactional"
    INFORMATIONAL = "informational"
    POLITICAL = "political"
    EMERGENCY = "emergency"


class ComplianceEventType(StrEnum):
    DNC_CHECK = "dnc_check"
    DNC_ADD = "dnc_add"
    DNC_REMOVE = "dnc_remove"
    CONSENT_RECORDED = "consent_recorded"
    CONSENT_REVOKED = "consent_revoked"
    BULK_UPLOAD = "bulk_upload"
    SMS_SYNC = "sms_sync"
    SETTINGS_CHANGED = "settings_changed"
    CALLING_WINDOW_BLOCKED = "calling_window_blocked"


# ── Models ──


class DNCList(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "dnc_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    list_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DNCListType.INTERNAL
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    # No eager-load for entries — lists can be huge. Always paginate separately.


class DNCEntry(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "dnc_entries"
    __table_args__ = (
        UniqueConstraint("dnc_list_id", "phone_number", name="uq_dnc_entries_list_phone"),
        Index("ix_dnc_entries_phone_number", "phone_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dnc_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dnc_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DNCEntrySource.MANUAL
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    dnc_list = relationship("DNCList", lazy="joined")
    added_by_user = relationship("User", lazy="joined")


class ConsentRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("ix_consent_records_phone_number", "phone_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_method: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant = relationship("Tenant", lazy="joined")
    recorded_by_user = relationship("User", lazy="joined")


class ComplianceSettings(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "compliance_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_compliance_settings_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calling_window_start: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(8, 0)
    )
    calling_window_end: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(21, 0)
    )
    default_timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="America/New_York"
    )
    enforce_calling_window: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    sync_sms_optout_to_dnc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    auto_dnc_on_request: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    national_dnc_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    tenant = relationship("Tenant", lazy="joined")


class ComplianceAuditLog(Base):
    """Immutable audit log for TCPA compliance events.

    No TimestampMixin (no updated_at). RLS policy: SELECT + INSERT only,
    no UPDATE/DELETE for the app role.
    """

    __tablename__ = "compliance_audit_logs"
    __table_args__ = (
        Index("ix_compliance_audit_logs_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    user = relationship("User", lazy="joined")
