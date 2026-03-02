import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.page_group import PageGroup, PageGroupMember
from new_phone.schemas.page_group import PageGroupCreate, PageGroupUpdate

logger = structlog.get_logger()


class PageGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_groups(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[PageGroup]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(PageGroup)
            .where(PageGroup.tenant_id == tenant_id, PageGroup.is_active.is_(True))
            .options(selectinload(PageGroup.members))
            .order_by(PageGroup.name)
        )
        if site_id is not None:
            stmt = stmt.where(PageGroup.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_group(self, tenant_id: uuid.UUID, group_id: uuid.UUID) -> PageGroup | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PageGroup)
            .where(
                PageGroup.id == group_id,
                PageGroup.tenant_id == tenant_id,
                PageGroup.is_active.is_(True),
            )
            .options(selectinload(PageGroup.members))
        )
        return result.scalar_one_or_none()

    async def create_group(self, tenant_id: uuid.UUID, data: PageGroupCreate) -> PageGroup:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate name
        existing = await self.db.execute(
            select(PageGroup).where(
                PageGroup.tenant_id == tenant_id,
                PageGroup.name == data.name,
                PageGroup.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Page group '{data.name}' already exists")

        # Check duplicate page_number
        existing = await self.db.execute(
            select(PageGroup).where(
                PageGroup.tenant_id == tenant_id,
                PageGroup.page_number == data.page_number,
                PageGroup.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Page number '{data.page_number}' already exists")

        group = PageGroup(
            tenant_id=tenant_id,
            name=data.name,
            page_number=data.page_number,
            description=data.description,
            page_mode=data.page_mode,
            timeout=data.timeout,
        )
        self.db.add(group)
        await self.db.flush()

        # Create members
        for m in data.members:
            member = PageGroupMember(
                page_group_id=group.id,
                extension_id=m.extension_id,
                position=m.position,
            )
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def update_group(
        self, tenant_id: uuid.UUID, group_id: uuid.UUID, data: PageGroupUpdate
    ) -> PageGroup:
        group = await self.get_group(tenant_id, group_id)
        if not group:
            raise ValueError("Page group not found")

        update_data = data.model_dump(exclude_unset=True)
        members_data = update_data.pop("members", None)

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != group.name:
            existing = await self.db.execute(
                select(PageGroup).where(
                    PageGroup.tenant_id == tenant_id,
                    PageGroup.name == update_data["name"],
                    PageGroup.is_active.is_(True),
                    PageGroup.id != group_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Page group '{update_data['name']}' already exists")

        # Check page_number uniqueness if changing
        if "page_number" in update_data and update_data["page_number"] != group.page_number:
            existing = await self.db.execute(
                select(PageGroup).where(
                    PageGroup.tenant_id == tenant_id,
                    PageGroup.page_number == update_data["page_number"],
                    PageGroup.is_active.is_(True),
                    PageGroup.id != group_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Page number '{update_data['page_number']}' already exists")

        for key, value in update_data.items():
            setattr(group, key, value)

        # Replace members wholesale if provided
        if members_data is not None:
            for m in list(group.members):
                await self.db.delete(m)
            await self.db.flush()
            for m_data in data.members:
                member = PageGroupMember(
                    page_group_id=group.id,
                    extension_id=m_data.extension_id,
                    position=m_data.position,
                )
                self.db.add(member)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def deactivate(self, tenant_id: uuid.UUID, group_id: uuid.UUID) -> PageGroup:
        group = await self.get_group(tenant_id, group_id)
        if not group:
            raise ValueError("Page group not found")
        group.is_active = False
        await self.db.commit()
        await self.db.refresh(group)
        return group
