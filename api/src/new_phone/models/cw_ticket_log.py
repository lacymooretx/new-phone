import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class CWTicketLog(Base):
    __tablename__ = "cw_ticket_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cw_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cw_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cdr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("call_detail_records.id", ondelete="SET NULL"), nullable=True
    )
    cw_ticket_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cw_company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ticket_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="created")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cw_config = relationship("CWConfig", lazy="joined")
    cdr = relationship("CallDetailRecord", lazy="joined")
