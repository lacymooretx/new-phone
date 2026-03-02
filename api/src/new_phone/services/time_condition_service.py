import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.time_condition import TimeCondition
from new_phone.schemas.time_condition import TimeConditionCreate, TimeConditionUpdate


class TimeConditionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_time_conditions(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[TimeCondition]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(TimeCondition)
            .where(TimeCondition.tenant_id == tenant_id, TimeCondition.is_active.is_(True))
            .order_by(TimeCondition.name)
        )
        if site_id is not None:
            stmt = stmt.where(TimeCondition.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_time_condition(
        self, tenant_id: uuid.UUID, tc_id: uuid.UUID
    ) -> TimeCondition | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(TimeCondition).where(
                TimeCondition.id == tc_id,
                TimeCondition.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_time_condition(
        self, tenant_id: uuid.UUID, data: TimeConditionCreate
    ) -> TimeCondition:
        await set_tenant_context(self.db, tenant_id)

        # Check for duplicate name
        existing = await self.db.execute(
            select(TimeCondition).where(
                TimeCondition.tenant_id == tenant_id,
                TimeCondition.name == data.name,
                TimeCondition.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Time condition '{data.name}' already exists")

        tc = TimeCondition(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            timezone=data.timezone,
            rules=[r.model_dump() for r in data.rules],
            match_destination_type=data.match_destination_type,
            match_destination_id=data.match_destination_id,
            nomatch_destination_type=data.nomatch_destination_type,
            nomatch_destination_id=data.nomatch_destination_id,
            enabled=data.enabled,
        )
        self.db.add(tc)
        await self.db.commit()
        await self.db.refresh(tc)
        return tc

    async def update_time_condition(
        self, tenant_id: uuid.UUID, tc_id: uuid.UUID, data: TimeConditionUpdate
    ) -> TimeCondition:
        tc = await self.get_time_condition(tenant_id, tc_id)
        if not tc:
            raise ValueError("Time condition not found")

        update_data = data.model_dump(exclude_unset=True)
        if "rules" in update_data and update_data["rules"] is not None:
            update_data["rules"] = [r.model_dump() if hasattr(r, "model_dump") else r for r in data.rules]
        for key, value in update_data.items():
            setattr(tc, key, value)

        await self.db.commit()
        await self.db.refresh(tc)
        return tc

    async def deactivate(
        self, tenant_id: uuid.UUID, tc_id: uuid.UUID
    ) -> TimeCondition:
        tc = await self.get_time_condition(tenant_id, tc_id)
        if not tc:
            raise ValueError("Time condition not found")
        tc.is_active = False
        await self.db.commit()
        await self.db.refresh(tc)
        return tc
