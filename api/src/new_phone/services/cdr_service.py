import csv
import io
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.disposition import DispositionCode
from new_phone.schemas.cdr import CDRFilter


class CDRService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cdrs(self, tenant_id: uuid.UUID, filters: CDRFilter) -> list[CallDetailRecord]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(CallDetailRecord).where(CallDetailRecord.tenant_id == tenant_id)

        if filters.date_from:
            stmt = stmt.where(CallDetailRecord.start_time >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(CallDetailRecord.start_time <= filters.date_to)
        if filters.extension_id:
            stmt = stmt.where(CallDetailRecord.extension_id == filters.extension_id)
        if filters.direction:
            stmt = stmt.where(CallDetailRecord.direction == filters.direction)
        if filters.disposition:
            stmt = stmt.where(CallDetailRecord.disposition == filters.disposition)
        if filters.agent_disposition_code_id:
            stmt = stmt.where(
                CallDetailRecord.agent_disposition_code_id == filters.agent_disposition_code_id
            )
        if filters.site_id:
            stmt = stmt.where(CallDetailRecord.site_id == filters.site_id)
        if filters.crm_customer_name:
            stmt = stmt.where(
                CallDetailRecord.crm_customer_name.ilike(f"%{filters.crm_customer_name}%")
            )
        if filters.crm_company_name:
            stmt = stmt.where(
                CallDetailRecord.crm_company_name.ilike(f"%{filters.crm_company_name}%")
            )
        if filters.crm_account_number:
            stmt = stmt.where(CallDetailRecord.crm_account_number == filters.crm_account_number)
        if filters.crm_matched is True:
            stmt = stmt.where(CallDetailRecord.crm_matched_at.is_not(None))
        elif filters.crm_matched is False:
            stmt = stmt.where(CallDetailRecord.crm_matched_at.is_(None))

        stmt = stmt.order_by(CallDetailRecord.start_time.desc())
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_cdr(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> CallDetailRecord | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(CallDetailRecord).where(
                CallDetailRecord.id == cdr_id,
                CallDetailRecord.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def export_csv(self, tenant_id: uuid.UUID, filters: CDRFilter) -> str:
        # Use a high limit for CSV export
        filters.limit = 10000
        cdrs = await self.list_cdrs(tenant_id, filters)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "call_id",
                "direction",
                "caller_number",
                "caller_name",
                "called_number",
                "disposition",
                "hangup_cause",
                "duration_seconds",
                "billable_seconds",
                "ring_seconds",
                "start_time",
                "answer_time",
                "end_time",
                "has_recording",
                "crm_customer_name",
                "crm_company_name",
                "crm_account_number",
                "crm_provider_type",
                "crm_deep_link_url",
            ]
        )
        for cdr in cdrs:
            writer.writerow(
                [
                    cdr.call_id,
                    cdr.direction,
                    cdr.caller_number,
                    cdr.caller_name,
                    cdr.called_number,
                    cdr.disposition,
                    cdr.hangup_cause or "",
                    cdr.duration_seconds,
                    cdr.billable_seconds,
                    cdr.ring_seconds,
                    cdr.start_time.isoformat(),
                    cdr.answer_time.isoformat() if cdr.answer_time else "",
                    cdr.end_time.isoformat(),
                    cdr.has_recording,
                    cdr.crm_customer_name or "",
                    cdr.crm_company_name or "",
                    cdr.crm_account_number or "",
                    cdr.crm_provider_type or "",
                    cdr.crm_deep_link_url or "",
                ]
            )
        return output.getvalue()

    async def set_disposition(
        self,
        tenant_id: uuid.UUID,
        cdr_id: uuid.UUID,
        code_id: uuid.UUID,
        notes: str | None = None,
    ) -> CallDetailRecord:
        await set_tenant_context(self.db, tenant_id)
        cdr = await self.get_cdr(tenant_id, cdr_id)
        if not cdr:
            raise ValueError("CDR not found")
        # Verify code exists and belongs to tenant
        result = await self.db.execute(
            select(DispositionCode).where(
                DispositionCode.id == code_id,
                DispositionCode.tenant_id == tenant_id,
            )
        )
        code = result.scalar_one_or_none()
        if not code:
            raise ValueError("Disposition code not found")
        cdr.agent_disposition_code_id = code_id
        cdr.agent_disposition_notes = notes
        cdr.disposition_entered_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(cdr)
        return cdr

    async def cleanup_old_cdrs(self, older_than: datetime) -> int:
        """Purge CDRs older than specified date. Admin only — no RLS context."""
        result = await self.db.execute(
            delete(CallDetailRecord).where(CallDetailRecord.start_time < older_than)
        )
        await self.db.commit()
        return result.rowcount
