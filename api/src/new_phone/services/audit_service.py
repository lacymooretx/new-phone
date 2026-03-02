import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.audit_log import AuditLog
from new_phone.schemas.audit_log import AuditLogListParams


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_entry(
        self,
        *,
        user_id: uuid.UUID | None,
        tenant_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        changes: dict | None = None,
        ip_address: str,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_entries(
        self, params: AuditLogListParams
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if params.tenant_id:
            query = query.where(AuditLog.tenant_id == params.tenant_id)
            count_query = count_query.where(AuditLog.tenant_id == params.tenant_id)
        if params.user_id:
            query = query.where(AuditLog.user_id == params.user_id)
            count_query = count_query.where(AuditLog.user_id == params.user_id)
        if params.action:
            query = query.where(AuditLog.action == params.action)
            count_query = count_query.where(AuditLog.action == params.action)
        if params.resource_type:
            query = query.where(AuditLog.resource_type == params.resource_type)
            count_query = count_query.where(AuditLog.resource_type == params.resource_type)
        if params.date_from:
            query = query.where(AuditLog.created_at >= params.date_from)
            count_query = count_query.where(AuditLog.created_at >= params.date_from)
        if params.date_to:
            query = query.where(AuditLog.created_at <= params.date_to)
            count_query = count_query.where(AuditLog.created_at <= params.date_to)

        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (params.page - 1) * params.per_page
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(params.per_page)

        result = await self.db.execute(query)
        entries = list(result.scalars().all())
        return entries, total
