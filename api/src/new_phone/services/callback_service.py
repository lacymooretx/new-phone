import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.scheduled_callback import CallbackStatus, ScheduledCallback

logger = structlog.get_logger()


class CallbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_callbacks(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID | None = None,
        status: str | None = None, page: int = 1, per_page: int = 50,
    ) -> tuple[list[ScheduledCallback], int]:
        await set_tenant_context(self.db, tenant_id)
        query = select(ScheduledCallback).where(ScheduledCallback.tenant_id == tenant_id)
        count_q = select(func.count(ScheduledCallback.id)).where(ScheduledCallback.tenant_id == tenant_id)

        if queue_id:
            query = query.where(ScheduledCallback.queue_id == queue_id)
            count_q = count_q.where(ScheduledCallback.queue_id == queue_id)
        if status:
            query = query.where(ScheduledCallback.status == status)
            count_q = count_q.where(ScheduledCallback.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(ScheduledCallback.scheduled_at.asc()).offset(offset).limit(per_page)
        )
        return list(result.scalars().all()), total

    async def get_callback(self, tenant_id: uuid.UUID, callback_id: uuid.UUID) -> ScheduledCallback | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ScheduledCallback).where(
                ScheduledCallback.id == callback_id,
                ScheduledCallback.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_callback(self, tenant_id: uuid.UUID, **kwargs) -> ScheduledCallback:
        await set_tenant_context(self.db, tenant_id)
        cb = ScheduledCallback(tenant_id=tenant_id, **kwargs)
        self.db.add(cb)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(cb)
        return cb

    async def update_callback(self, tenant_id: uuid.UUID, callback_id: uuid.UUID, **updates) -> ScheduledCallback | None:
        cb = await self.get_callback(tenant_id, callback_id)
        if not cb:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(cb, k):
                setattr(cb, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(cb)
        return cb

    async def cancel_callback(self, tenant_id: uuid.UUID, callback_id: uuid.UUID) -> bool:
        cb = await self.get_callback(tenant_id, callback_id)
        if not cb or cb.status in (CallbackStatus.COMPLETED, CallbackStatus.CANCELLED):
            return False
        cb.status = CallbackStatus.CANCELLED
        await self.db.flush()
        await self.db.commit()
        return True

    async def get_due_callbacks(self, tenant_id: uuid.UUID) -> list[ScheduledCallback]:
        """Get callbacks that are due for execution."""
        await set_tenant_context(self.db, tenant_id)
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(ScheduledCallback).where(
                ScheduledCallback.tenant_id == tenant_id,
                ScheduledCallback.status.in_([CallbackStatus.PENDING, CallbackStatus.SCHEDULED]),
                ScheduledCallback.scheduled_at <= now,
            ).order_by(ScheduledCallback.scheduled_at.asc())
        )
        return list(result.scalars().all())
