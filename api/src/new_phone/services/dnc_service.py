import uuid
from datetime import datetime, time

import pytz
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.dnc import (
    ComplianceAuditLog,
    ComplianceEventType,
    ComplianceSettings,
    ConsentRecord,
    DNCEntry,
    DNCEntrySource,
    DNCList,
    DNCListType,
)
from new_phone.models.sms import SMSOptOut
from new_phone.schemas.dnc import (
    BulkUploadResult,
    ComplianceSettingsUpdate,
    ConsentRecordCreate,
    DNCCheckResult,
    DNCEntryCreate,
    DNCListCreate,
    DNCListUpdate,
)


class DNCService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── DNC Lists ──

    async def list_dnc_lists(self, tenant_id: uuid.UUID) -> list[DNCList]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DNCList)
            .where(DNCList.tenant_id == tenant_id, DNCList.is_active.is_(True))
            .order_by(DNCList.name)
        )
        return list(result.scalars().unique().all())

    async def create_dnc_list(
        self, tenant_id: uuid.UUID, data: DNCListCreate
    ) -> DNCList:
        await set_tenant_context(self.db, tenant_id)
        dnc_list = DNCList(tenant_id=tenant_id, **data.model_dump())
        self.db.add(dnc_list)
        await self._audit(
            tenant_id,
            ComplianceEventType.DNC_ADD,
            details={"action": "list_created", "list_name": data.name},
        )
        await self.db.commit()
        await self.db.refresh(dnc_list)
        return dnc_list

    async def get_dnc_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID
    ) -> DNCList | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DNCList).where(
                DNCList.id == list_id, DNCList.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_dnc_list_with_count(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID
    ) -> tuple[DNCList | None, int]:
        dnc_list = await self.get_dnc_list(tenant_id, list_id)
        if not dnc_list:
            return None, 0
        count = await self._entry_count(list_id)
        return dnc_list, count

    async def update_dnc_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID, data: DNCListUpdate
    ) -> DNCList:
        dnc_list = await self.get_dnc_list(tenant_id, list_id)
        if not dnc_list:
            raise ValueError("DNC list not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(dnc_list, key, value)
        await self.db.commit()
        await self.db.refresh(dnc_list)
        return dnc_list

    async def delete_dnc_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID
    ) -> DNCList:
        dnc_list = await self.get_dnc_list(tenant_id, list_id)
        if not dnc_list:
            raise ValueError("DNC list not found")
        dnc_list.is_active = False
        await self._audit(
            tenant_id,
            ComplianceEventType.DNC_REMOVE,
            details={"action": "list_deactivated", "list_name": dnc_list.name},
        )
        await self.db.commit()
        await self.db.refresh(dnc_list)
        return dnc_list

    # ── DNC Entries ──

    async def list_entries(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID, page: int = 1, per_page: int = 50
    ) -> tuple[list[DNCEntry], int]:
        await set_tenant_context(self.db, tenant_id)
        # Count
        count_result = await self.db.execute(
            select(func.count()).select_from(DNCEntry).where(
                DNCEntry.dnc_list_id == list_id, DNCEntry.tenant_id == tenant_id
            )
        )
        total = count_result.scalar_one()
        # Items
        result = await self.db.execute(
            select(DNCEntry)
            .where(DNCEntry.dnc_list_id == list_id, DNCEntry.tenant_id == tenant_id)
            .order_by(DNCEntry.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return list(result.scalars().unique().all()), total

    async def add_entry(
        self,
        tenant_id: uuid.UUID,
        list_id: uuid.UUID,
        data: DNCEntryCreate,
        user_id: uuid.UUID | None = None,
    ) -> DNCEntry:
        await set_tenant_context(self.db, tenant_id)
        entry = DNCEntry(
            tenant_id=tenant_id,
            dnc_list_id=list_id,
            added_by_user_id=user_id,
            **data.model_dump(),
        )
        self.db.add(entry)
        await self._audit(
            tenant_id,
            ComplianceEventType.DNC_ADD,
            phone_number=data.phone_number,
            user_id=user_id,
            details={"list_id": str(list_id), "source": data.source},
        )
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def bulk_add_entries(
        self,
        tenant_id: uuid.UUID,
        list_id: uuid.UUID,
        phone_numbers: list[str],
        user_id: uuid.UUID | None = None,
        reason: str | None = None,
        source: str = DNCEntrySource.BULK_UPLOAD,
    ) -> BulkUploadResult:
        await set_tenant_context(self.db, tenant_id)
        total = len(phone_numbers)
        # Deduplicate input
        unique_numbers = list(dict.fromkeys(phone_numbers))

        values = [
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "dnc_list_id": list_id,
                "phone_number": pn,
                "added_by_user_id": user_id,
                "reason": reason,
                "source": source,
            }
            for pn in unique_numbers
        ]

        stmt = pg_insert(DNCEntry).values(values)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_dnc_entries_list_phone"
        )
        result = await self.db.execute(stmt)
        added = result.rowcount

        await self._audit(
            tenant_id,
            ComplianceEventType.BULK_UPLOAD,
            user_id=user_id,
            details={
                "list_id": str(list_id),
                "total_submitted": total,
                "added": added,
                "skipped": total - added,
            },
        )
        await self.db.commit()
        return BulkUploadResult(added=added, skipped=total - added, total=total)

    async def remove_entry(
        self,
        tenant_id: uuid.UUID,
        list_id: uuid.UUID,
        entry_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DNCEntry).where(
                DNCEntry.id == entry_id,
                DNCEntry.dnc_list_id == list_id,
                DNCEntry.tenant_id == tenant_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("DNC entry not found")

        await self._audit(
            tenant_id,
            ComplianceEventType.DNC_REMOVE,
            phone_number=entry.phone_number,
            user_id=user_id,
            details={"list_id": str(list_id), "entry_id": str(entry_id)},
        )
        await self.db.execute(
            delete(DNCEntry).where(DNCEntry.id == entry_id)
        )
        await self.db.commit()

    # ── DNC Check (Core) ──

    async def check_number(
        self, tenant_id: uuid.UUID, phone_number: str, user_id: uuid.UUID | None = None
    ) -> DNCCheckResult:
        await set_tenant_context(self.db, tenant_id)

        # Check all active DNC lists for this phone number
        result = await self.db.execute(
            select(DNCList.name)
            .join(DNCEntry, DNCEntry.dnc_list_id == DNCList.id)
            .where(
                DNCEntry.phone_number == phone_number,
                DNCEntry.tenant_id == tenant_id,
                DNCList.is_active.is_(True),
            )
        )
        matched_lists = [row[0] for row in result.all()]
        is_blocked = len(matched_lists) > 0

        # Check consent
        consent_result = await self.db.execute(
            select(ConsentRecord).where(
                ConsentRecord.phone_number == phone_number,
                ConsentRecord.tenant_id == tenant_id,
                ConsentRecord.is_active.is_(True),
            )
        )
        has_consent = consent_result.scalar_one_or_none() is not None

        # Check calling window
        calling_window_ok = await self.check_calling_window(tenant_id)

        check_result = DNCCheckResult(
            is_blocked=is_blocked,
            matched_lists=matched_lists,
            has_consent=has_consent,
            calling_window_ok=calling_window_ok,
            details={
                "dnc_lists_checked": len(matched_lists),
                "consent_active": has_consent,
            },
        )

        await self._audit(
            tenant_id,
            ComplianceEventType.DNC_CHECK,
            phone_number=phone_number,
            user_id=user_id,
            details={
                "is_blocked": is_blocked,
                "matched_lists": matched_lists,
                "has_consent": has_consent,
                "calling_window_ok": calling_window_ok,
            },
        )
        await self.db.commit()
        return check_result

    async def check_calling_window(self, tenant_id: uuid.UUID) -> bool:
        settings = await self.get_settings(tenant_id)
        if not settings.enforce_calling_window:
            return True

        try:
            tz = pytz.timezone(settings.default_timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("America/New_York")

        now = datetime.now(tz).time()
        return settings.calling_window_start <= now <= settings.calling_window_end

    # ── Consent Records ──

    async def list_consent_records(
        self,
        tenant_id: uuid.UUID,
        phone_number: str | None = None,
        campaign_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[ConsentRecord], int]:
        await set_tenant_context(self.db, tenant_id)

        query = select(ConsentRecord).where(ConsentRecord.tenant_id == tenant_id)
        count_query = select(func.count()).select_from(ConsentRecord).where(
            ConsentRecord.tenant_id == tenant_id
        )

        if phone_number:
            query = query.where(ConsentRecord.phone_number == phone_number)
            count_query = count_query.where(ConsentRecord.phone_number == phone_number)
        if campaign_type:
            query = query.where(ConsentRecord.campaign_type == campaign_type)
            count_query = count_query.where(ConsentRecord.campaign_type == campaign_type)
        if is_active is not None:
            query = query.where(ConsentRecord.is_active.is_(is_active))
            count_query = count_query.where(ConsentRecord.is_active.is_(is_active))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(ConsentRecord.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return list(result.scalars().unique().all()), total

    async def create_consent_record(
        self,
        tenant_id: uuid.UUID,
        data: ConsentRecordCreate,
        user_id: uuid.UUID | None = None,
    ) -> ConsentRecord:
        await set_tenant_context(self.db, tenant_id)
        record = ConsentRecord(
            tenant_id=tenant_id,
            phone_number=data.phone_number,
            campaign_type=data.campaign_type,
            consent_method=data.consent_method,
            consent_text=data.consent_text,
            consented_at=data.consented_at or datetime.now(pytz.UTC),
            is_active=True,
            metadata_json=data.metadata,
            recorded_by_user_id=user_id,
        )
        self.db.add(record)
        await self._audit(
            tenant_id,
            ComplianceEventType.CONSENT_RECORDED,
            phone_number=data.phone_number,
            user_id=user_id,
            details={
                "campaign_type": data.campaign_type,
                "consent_method": data.consent_method,
            },
        )
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def revoke_consent(
        self,
        tenant_id: uuid.UUID,
        record_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> ConsentRecord:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ConsentRecord).where(
                ConsentRecord.id == record_id,
                ConsentRecord.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError("Consent record not found")

        record.is_active = False
        record.revoked_at = datetime.now(pytz.UTC)
        await self._audit(
            tenant_id,
            ComplianceEventType.CONSENT_REVOKED,
            phone_number=record.phone_number,
            user_id=user_id,
            details={
                "record_id": str(record_id),
                "campaign_type": record.campaign_type,
            },
        )
        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ── Compliance Settings ──

    async def get_settings(self, tenant_id: uuid.UUID) -> ComplianceSettings:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ComplianceSettings).where(
                ComplianceSettings.tenant_id == tenant_id
            )
        )
        settings = result.scalar_one_or_none()
        if not settings:
            # Upsert: create defaults on first access
            settings = ComplianceSettings(
                tenant_id=tenant_id,
                calling_window_start=time(8, 0),
                calling_window_end=time(21, 0),
                default_timezone="America/New_York",
                enforce_calling_window=True,
                sync_sms_optout_to_dnc=False,
                auto_dnc_on_request=True,
                national_dnc_enabled=False,
            )
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def update_settings(
        self,
        tenant_id: uuid.UUID,
        data: ComplianceSettingsUpdate,
        user_id: uuid.UUID | None = None,
    ) -> ComplianceSettings:
        settings = await self.get_settings(tenant_id)
        changes = data.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(settings, key, value)
        await self._audit(
            tenant_id,
            ComplianceEventType.SETTINGS_CHANGED,
            user_id=user_id,
            details={"changes": {k: str(v) for k, v in changes.items()}},
        )
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    # ── Audit Log ──

    async def list_audit_log(
        self,
        tenant_id: uuid.UUID,
        event_type: str | None = None,
        phone_number: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[ComplianceAuditLog], int]:
        await set_tenant_context(self.db, tenant_id)

        query = select(ComplianceAuditLog).where(
            ComplianceAuditLog.tenant_id == tenant_id
        )
        count_query = select(func.count()).select_from(ComplianceAuditLog).where(
            ComplianceAuditLog.tenant_id == tenant_id
        )

        if event_type:
            query = query.where(ComplianceAuditLog.event_type == event_type)
            count_query = count_query.where(ComplianceAuditLog.event_type == event_type)
        if phone_number:
            query = query.where(ComplianceAuditLog.phone_number == phone_number)
            count_query = count_query.where(ComplianceAuditLog.phone_number == phone_number)
        if start_date:
            query = query.where(ComplianceAuditLog.created_at >= start_date)
            count_query = count_query.where(ComplianceAuditLog.created_at >= start_date)
        if end_date:
            query = query.where(ComplianceAuditLog.created_at <= end_date)
            count_query = count_query.where(ComplianceAuditLog.created_at <= end_date)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(ComplianceAuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return list(result.scalars().unique().all()), total

    # ── SMS Opt-Out Sync ──

    async def sync_sms_optouts_to_dnc(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> BulkUploadResult:
        await set_tenant_context(self.db, tenant_id)

        # Find or create the "Internal - SMS Opt-Outs" DNC list
        result = await self.db.execute(
            select(DNCList).where(
                DNCList.tenant_id == tenant_id,
                DNCList.name == "Internal - SMS Opt-Outs",
                DNCList.list_type == DNCListType.INTERNAL,
            )
        )
        dnc_list = result.scalar_one_or_none()
        if not dnc_list:
            dnc_list = DNCList(
                tenant_id=tenant_id,
                name="Internal - SMS Opt-Outs",
                description="Auto-synced from SMS opt-out records",
                list_type=DNCListType.INTERNAL,
                is_active=True,
            )
            self.db.add(dnc_list)
            await self.db.flush()

        # Get all opted-out phone numbers
        opt_out_result = await self.db.execute(
            select(SMSOptOut.phone_number).where(
                SMSOptOut.tenant_id == tenant_id,
                SMSOptOut.is_opted_out.is_(True),
            )
        )
        phone_numbers = list({row[0] for row in opt_out_result.all()})

        if not phone_numbers:
            await self._audit(
                tenant_id,
                ComplianceEventType.SMS_SYNC,
                user_id=user_id,
                details={"message": "No opted-out numbers found"},
            )
            await self.db.commit()
            return BulkUploadResult(added=0, skipped=0, total=0)

        # Bulk insert with conflict handling
        values = [
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "dnc_list_id": dnc_list.id,
                "phone_number": pn,
                "added_by_user_id": user_id,
                "reason": "SMS opt-out sync",
                "source": DNCEntrySource.SMS_SYNC,
            }
            for pn in phone_numbers
        ]
        stmt = pg_insert(DNCEntry).values(values)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_dnc_entries_list_phone")
        insert_result = await self.db.execute(stmt)
        added = insert_result.rowcount

        await self._audit(
            tenant_id,
            ComplianceEventType.SMS_SYNC,
            user_id=user_id,
            details={
                "list_id": str(dnc_list.id),
                "total_opt_outs": len(phone_numbers),
                "added": added,
                "skipped": len(phone_numbers) - added,
            },
        )
        await self.db.commit()
        return BulkUploadResult(
            added=added, skipped=len(phone_numbers) - added, total=len(phone_numbers)
        )

    # ── Private Helpers ──

    async def _entry_count(self, list_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(DNCEntry).where(
                DNCEntry.dnc_list_id == list_id
            )
        )
        return result.scalar_one()

    async def _audit(
        self,
        tenant_id: uuid.UUID,
        event_type: ComplianceEventType,
        phone_number: str | None = None,
        user_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> None:
        log = ComplianceAuditLog(
            tenant_id=tenant_id,
            event_type=event_type,
            phone_number=phone_number,
            user_id=user_id,
            details=details,
        )
        self.db.add(log)
