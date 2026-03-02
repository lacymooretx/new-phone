import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.outbound_route import OutboundRoute, OutboundRouteTrunk
from new_phone.schemas.outbound_route import OutboundRouteCreate, OutboundRouteUpdate


class OutboundRouteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_outbound_routes(self, tenant_id: uuid.UUID) -> list[OutboundRoute]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(OutboundRoute)
            .where(OutboundRoute.tenant_id == tenant_id, OutboundRoute.is_active.is_(True))
            .order_by(OutboundRoute.priority, OutboundRoute.name)
        )
        return list(result.scalars().unique().all())

    async def get_outbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> OutboundRoute | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(OutboundRoute).where(
                OutboundRoute.id == route_id, OutboundRoute.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_outbound_route(
        self, tenant_id: uuid.UUID, data: OutboundRouteCreate
    ) -> OutboundRoute:
        await set_tenant_context(self.db, tenant_id)
        route_data = data.model_dump(exclude={"trunk_ids"})
        route = OutboundRoute(tenant_id=tenant_id, **route_data)
        self.db.add(route)
        await self.db.flush()

        # Add trunk assignments
        for position, trunk_id in enumerate(data.trunk_ids):
            assignment = OutboundRouteTrunk(
                outbound_route_id=route.id,
                trunk_id=trunk_id,
                position=position,
            )
            self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def update_outbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID, data: OutboundRouteUpdate
    ) -> OutboundRoute:
        route = await self.get_outbound_route(tenant_id, route_id)
        if not route:
            raise ValueError("Outbound route not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"trunk_ids"})
        for key, value in update_data.items():
            setattr(route, key, value)

        # Replace trunk assignments if provided
        if data.trunk_ids is not None:
            await self.db.execute(
                delete(OutboundRouteTrunk).where(
                    OutboundRouteTrunk.outbound_route_id == route_id
                )
            )
            for position, trunk_id in enumerate(data.trunk_ids):
                assignment = OutboundRouteTrunk(
                    outbound_route_id=route_id,
                    trunk_id=trunk_id,
                    position=position,
                )
                self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def deactivate_outbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> OutboundRoute:
        route = await self.get_outbound_route(tenant_id, route_id)
        if not route:
            raise ValueError("Outbound route not found")

        route.is_active = False
        route.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(route)
        return route
