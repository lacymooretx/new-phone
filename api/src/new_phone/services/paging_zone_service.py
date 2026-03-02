import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.paging_zone import PagingZone, PagingZoneMember
from new_phone.schemas.paging_zone import PagingZoneCreate, PagingZoneUpdate

logger = structlog.get_logger()


class PagingZoneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_zones(self, tenant_id: uuid.UUID) -> list[PagingZone]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PagingZone)
            .where(PagingZone.tenant_id == tenant_id, PagingZone.is_active.is_(True))
            .options(selectinload(PagingZone.members))
            .order_by(PagingZone.priority, PagingZone.name)
        )
        return list(result.scalars().all())

    async def get_zone(self, tenant_id: uuid.UUID, zone_id: uuid.UUID) -> PagingZone | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PagingZone)
            .where(PagingZone.id == zone_id, PagingZone.tenant_id == tenant_id)
            .options(selectinload(PagingZone.members))
        )
        return result.scalar_one_or_none()

    async def create_zone(self, tenant_id: uuid.UUID, data: PagingZoneCreate) -> PagingZone:
        await set_tenant_context(self.db, tenant_id)

        # Check for duplicate zone_number
        existing = await self.db.execute(
            select(PagingZone).where(
                PagingZone.tenant_id == tenant_id,
                PagingZone.zone_number == data.zone_number,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Zone number '{data.zone_number}' already exists")

        zone = PagingZone(
            tenant_id=tenant_id,
            name=data.name,
            zone_number=data.zone_number,
            description=data.description,
            is_emergency=data.is_emergency,
            priority=data.priority,
            site_id=data.site_id,
        )
        self.db.add(zone)
        await self.db.flush()

        # Create members
        for member_data in data.members:
            member = PagingZoneMember(
                paging_zone_id=zone.id,
                extension_id=member_data.extension_id,
                position=member_data.position,
            )
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def update_zone(
        self, tenant_id: uuid.UUID, zone_id: uuid.UUID, data: PagingZoneUpdate
    ) -> PagingZone:
        zone = await self.get_zone(tenant_id, zone_id)
        if not zone:
            raise ValueError("Paging zone not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"members"})
        for key, value in update_data.items():
            setattr(zone, key, value)

        # Replace members if provided
        if data.members is not None:
            # Delete existing members
            for existing_member in list(zone.members):
                await self.db.delete(existing_member)
            await self.db.flush()

            # Create new members
            for member_data in data.members:
                member = PagingZoneMember(
                    paging_zone_id=zone.id,
                    extension_id=member_data.extension_id,
                    position=member_data.position,
                )
                self.db.add(member)

        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def deactivate_zone(self, tenant_id: uuid.UUID, zone_id: uuid.UUID) -> PagingZone:
        zone = await self.get_zone(tenant_id, zone_id)
        if not zone:
            raise ValueError("Paging zone not found")
        zone.is_active = False
        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def trigger_emergency_allcall(self, tenant_id: uuid.UUID) -> list[PagingZone]:
        """Trigger an emergency all-call across all emergency paging zones."""
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PagingZone)
            .where(
                PagingZone.tenant_id == tenant_id,
                PagingZone.is_emergency.is_(True),
                PagingZone.is_active.is_(True),
            )
            .options(selectinload(PagingZone.members))
        )
        zones = list(result.scalars().all())
        logger.info(
            "emergency_allcall_triggered",
            tenant_id=str(tenant_id),
            zone_count=len(zones),
        )
        return zones
