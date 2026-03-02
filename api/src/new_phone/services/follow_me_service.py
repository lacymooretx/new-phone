import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.follow_me import FollowMe, FollowMeDestination
from new_phone.schemas.follow_me import FollowMeUpdate


class FollowMeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_follow_me(
        self, tenant_id: uuid.UUID, extension_id: uuid.UUID
    ) -> FollowMe | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(FollowMe)
            .where(
                FollowMe.tenant_id == tenant_id,
                FollowMe.extension_id == extension_id,
                FollowMe.is_active.is_(True),
            )
            .options(selectinload(FollowMe.destinations))
        )
        return result.scalar_one_or_none()

    async def upsert_follow_me(
        self, tenant_id: uuid.UUID, extension_id: uuid.UUID, data: FollowMeUpdate
    ) -> FollowMe:
        await set_tenant_context(self.db, tenant_id)

        # Try to find existing
        result = await self.db.execute(
            select(FollowMe)
            .where(
                FollowMe.tenant_id == tenant_id,
                FollowMe.extension_id == extension_id,
            )
            .options(selectinload(FollowMe.destinations))
        )
        fm = result.scalar_one_or_none()

        if fm:
            # Update existing
            fm.enabled = data.enabled
            fm.strategy = data.strategy
            fm.ring_extension_first = data.ring_extension_first
            fm.extension_ring_time = data.extension_ring_time
            fm.is_active = True

            # Replace all destinations
            await self.db.execute(
                delete(FollowMeDestination).where(
                    FollowMeDestination.follow_me_id == fm.id
                )
            )
        else:
            # Create new
            fm = FollowMe(
                tenant_id=tenant_id,
                extension_id=extension_id,
                enabled=data.enabled,
                strategy=data.strategy,
                ring_extension_first=data.ring_extension_first,
                extension_ring_time=data.extension_ring_time,
            )
            self.db.add(fm)
            await self.db.flush()

        # Add new destinations
        for position, dest_data in enumerate(data.destinations):
            dest = FollowMeDestination(
                follow_me_id=fm.id,
                position=position,
                destination=dest_data.destination,
                ring_time=dest_data.ring_time,
            )
            self.db.add(dest)

        await self.db.commit()
        await self.db.refresh(fm)
        return fm
