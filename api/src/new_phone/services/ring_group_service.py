import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.ring_group import RingGroup, RingGroupMember
from new_phone.schemas.ring_group import RingGroupCreate, RingGroupUpdate


class RingGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_ring_groups(self, tenant_id: uuid.UUID) -> list[RingGroup]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(RingGroup)
            .where(RingGroup.tenant_id == tenant_id, RingGroup.is_active.is_(True))
            .order_by(RingGroup.group_number)
        )
        return list(result.scalars().unique().all())

    async def get_ring_group(
        self, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> RingGroup | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(RingGroup).where(
                RingGroup.id == group_id, RingGroup.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_ring_group(
        self, tenant_id: uuid.UUID, data: RingGroupCreate
    ) -> RingGroup:
        await set_tenant_context(self.db, tenant_id)
        # Check duplicate group number
        existing = await self.db.execute(
            select(RingGroup).where(
                RingGroup.tenant_id == tenant_id,
                RingGroup.group_number == data.group_number,
                RingGroup.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Ring group number '{data.group_number}' already exists"
            )

        group_data = data.model_dump(exclude={"member_extension_ids"})
        group = RingGroup(tenant_id=tenant_id, **group_data)
        self.db.add(group)
        await self.db.flush()

        # Add members
        for position, ext_id in enumerate(data.member_extension_ids):
            member = RingGroupMember(
                ring_group_id=group.id,
                extension_id=ext_id,
                position=position,
            )
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def update_ring_group(
        self, tenant_id: uuid.UUID, group_id: uuid.UUID, data: RingGroupUpdate
    ) -> RingGroup:
        group = await self.get_ring_group(tenant_id, group_id)
        if not group:
            raise ValueError("Ring group not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"member_extension_ids"})
        for key, value in update_data.items():
            setattr(group, key, value)

        # Replace members if provided
        if data.member_extension_ids is not None:
            await self.db.execute(
                delete(RingGroupMember).where(
                    RingGroupMember.ring_group_id == group_id
                )
            )
            for position, ext_id in enumerate(data.member_extension_ids):
                member = RingGroupMember(
                    ring_group_id=group_id,
                    extension_id=ext_id,
                    position=position,
                )
                self.db.add(member)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def deactivate_ring_group(
        self, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> RingGroup:
        group = await self.get_ring_group(tenant_id, group_id)
        if not group:
            raise ValueError("Ring group not found")

        group.is_active = False
        group.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(group)
        return group
