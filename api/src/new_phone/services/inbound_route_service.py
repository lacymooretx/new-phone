import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.inbound_route import InboundRoute
from new_phone.schemas.inbound_route import InboundRouteCreate, InboundRouteUpdate


class InboundRouteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_inbound_routes(self, tenant_id: uuid.UUID) -> list[InboundRoute]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(InboundRoute)
            .where(InboundRoute.tenant_id == tenant_id, InboundRoute.is_active.is_(True))
            .order_by(InboundRoute.name)
        )
        return list(result.scalars().all())

    async def get_inbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> InboundRoute | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(InboundRoute).where(
                InboundRoute.id == route_id, InboundRoute.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_inbound_route(
        self, tenant_id: uuid.UUID, data: InboundRouteCreate
    ) -> InboundRoute:
        await set_tenant_context(self.db, tenant_id)
        route = InboundRoute(tenant_id=tenant_id, **data.model_dump())
        self.db.add(route)
        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def update_inbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID, data: InboundRouteUpdate
    ) -> InboundRoute:
        route = await self.get_inbound_route(tenant_id, route_id)
        if not route:
            raise ValueError("Inbound route not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(route, key, value)

        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def deactivate_inbound_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> InboundRoute:
        route = await self.get_inbound_route(tenant_id, route_id)
        if not route:
            raise ValueError("Inbound route not found")

        route.is_active = False
        route.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(route)
        return route
