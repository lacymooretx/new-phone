import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class CallDetailRecord(Base):
    __tablename__ = "call_detail_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    caller_number: Mapped[str] = mapped_column(String(40), nullable=False, server_default="")
    caller_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    called_number: Mapped[str] = mapped_column(String(40), nullable=False, server_default="")

    extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True
    )
    did_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dids.id", ondelete="SET NULL"), nullable=True
    )
    trunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True
    )
    ring_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ring_groups.id", ondelete="SET NULL"), nullable=True
    )
    queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queues.id", ondelete="SET NULL"), nullable=True
    )

    disposition: Mapped[str] = mapped_column(String(30), nullable=False)
    hangup_cause: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    billable_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ring_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answer_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    has_recording: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Agent disposition (post-call wrap-up)
    agent_disposition_code_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disposition_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition_entered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ConnectWise integration
    connectwise_ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Boss/admin on-behalf-of tracking
    answered_by_extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True
    )
    on_behalf_of_extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # CRM enrichment
    crm_customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crm_account_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    crm_contact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_provider_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    crm_deep_link_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    crm_custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    crm_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Compliance monitoring
    compliance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    compliance_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tenant = relationship("Tenant", lazy="joined")
    recordings = relationship("Recording", back_populates="cdr", lazy="selectin")
    agent_disposition_code = relationship("DispositionCode", lazy="joined")
    answered_by_extension = relationship(
        "Extension", foreign_keys=[answered_by_extension_id], lazy="joined"
    )
    on_behalf_of_extension = relationship(
        "Extension", foreign_keys=[on_behalf_of_extension_id], lazy="joined"
    )
    site = relationship("Site", lazy="joined")
    compliance_evaluation = relationship("ComplianceEvaluation", foreign_keys=[compliance_evaluation_id], lazy="joined")
