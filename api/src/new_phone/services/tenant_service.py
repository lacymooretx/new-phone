import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.tenant import Tenant
from new_phone.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tenants(self) -> list[Tenant]:
        result = await self.db.execute(select(Tenant).order_by(Tenant.name))
        return list(result.scalars().all())

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_tenant_by_sip_domain(self, sip_domain: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.sip_domain == sip_domain)
        )
        return result.scalar_one_or_none()

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        existing = await self.get_tenant_by_slug(data.slug)
        if existing:
            raise ValueError(f"Tenant with slug '{data.slug}' already exists")

        tenant_data = data.model_dump()
        # Auto-generate sip_domain from slug if not provided
        if not tenant_data.get("sip_domain"):
            tenant_data["sip_domain"] = f"{data.slug}.sip.local"

        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def update_tenant(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        tenant.is_active = False
        tenant.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
