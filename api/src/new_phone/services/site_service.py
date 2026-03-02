import uuid
import zoneinfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.site import Site
from new_phone.schemas.site import SiteCreate, SiteUpdate


class SiteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sites(self, tenant_id: uuid.UUID) -> list[Site]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Site)
            .where(Site.tenant_id == tenant_id, Site.is_active.is_(True))
            .order_by(Site.name)
        )
        return list(result.scalars().all())

    async def get_site(self, tenant_id: uuid.UUID, site_id: uuid.UUID) -> Site | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Site).where(
                Site.id == site_id,
                Site.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_site(self, tenant_id: uuid.UUID, data: SiteCreate) -> Site:
        await set_tenant_context(self.db, tenant_id)

        # Validate timezone
        if data.timezone not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid timezone: '{data.timezone}'")

        # Check duplicate name
        existing = await self.db.execute(
            select(Site).where(
                Site.tenant_id == tenant_id,
                Site.name == data.name,
                Site.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Site '{data.name}' already exists")

        site = Site(tenant_id=tenant_id, **data.model_dump())
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def update_site(
        self, tenant_id: uuid.UUID, site_id: uuid.UUID, data: SiteUpdate
    ) -> Site:
        site = await self.get_site(tenant_id, site_id)
        if not site:
            raise ValueError("Site not found")

        update_data = data.model_dump(exclude_unset=True)

        # Validate timezone if changing
        if (
            "timezone" in update_data
            and update_data["timezone"] is not None
            and update_data["timezone"] not in zoneinfo.available_timezones()
        ):
            raise ValueError(f"Invalid timezone: '{update_data['timezone']}'")

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != site.name:
            existing = await self.db.execute(
                select(Site).where(
                    Site.tenant_id == tenant_id,
                    Site.name == update_data["name"],
                    Site.is_active.is_(True),
                    Site.id != site_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Site '{update_data['name']}' already exists")

        for key, value in update_data.items():
            setattr(site, key, value)

        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def deactivate(self, tenant_id: uuid.UUID, site_id: uuid.UUID) -> Site:
        site = await self.get_site(tenant_id, site_id)
        if not site:
            raise ValueError("Site not found")
        site.is_active = False
        await self.db.commit()
        await self.db.refresh(site)
        return site
