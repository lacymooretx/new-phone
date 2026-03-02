import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from new_phone.db.rls import set_tenant_context
from new_phone.models.boss_admin import BossAdminRelationship
from new_phone.models.extension import Extension
from new_phone.schemas.boss_admin import BossAdminCreate, BossAdminUpdate


class BossAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_relationships(
        self,
        tenant_id: uuid.UUID,
        executive_id: uuid.UUID | None = None,
        assistant_id: uuid.UUID | None = None,
    ) -> list[BossAdminRelationship]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(BossAdminRelationship)
            .where(BossAdminRelationship.tenant_id == tenant_id)
            .options(
                joinedload(BossAdminRelationship.executive_extension),
                joinedload(BossAdminRelationship.assistant_extension),
            )
            .order_by(BossAdminRelationship.created_at)
        )
        if executive_id:
            stmt = stmt.where(BossAdminRelationship.executive_extension_id == executive_id)
        if assistant_id:
            stmt = stmt.where(BossAdminRelationship.assistant_extension_id == assistant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def create_relationship(
        self, tenant_id: uuid.UUID, data: BossAdminCreate
    ) -> BossAdminRelationship:
        await set_tenant_context(self.db, tenant_id)
        await self.validate_extensions(
            tenant_id, data.executive_extension_id, data.assistant_extension_id
        )

        # Check for duplicate
        existing = await self.db.execute(
            select(BossAdminRelationship).where(
                BossAdminRelationship.tenant_id == tenant_id,
                BossAdminRelationship.executive_extension_id == data.executive_extension_id,
                BossAdminRelationship.assistant_extension_id == data.assistant_extension_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("This boss/admin relationship already exists")

        rel = BossAdminRelationship(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)
        return rel

    async def get_relationship(
        self, tenant_id: uuid.UUID, relationship_id: uuid.UUID
    ) -> BossAdminRelationship | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BossAdminRelationship)
            .where(
                BossAdminRelationship.id == relationship_id,
                BossAdminRelationship.tenant_id == tenant_id,
            )
            .options(
                joinedload(BossAdminRelationship.executive_extension),
                joinedload(BossAdminRelationship.assistant_extension),
            )
        )
        return result.scalar_one_or_none()

    async def update_relationship(
        self,
        tenant_id: uuid.UUID,
        relationship_id: uuid.UUID,
        data: BossAdminUpdate,
    ) -> BossAdminRelationship:
        rel = await self.get_relationship(tenant_id, relationship_id)
        if not rel:
            raise ValueError("Boss/admin relationship not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rel, key, value)

        await self.db.commit()
        await self.db.refresh(rel)
        return rel

    async def delete_relationship(
        self, tenant_id: uuid.UUID, relationship_id: uuid.UUID
    ) -> None:
        rel = await self.get_relationship(tenant_id, relationship_id)
        if not rel:
            raise ValueError("Boss/admin relationship not found")
        await self.db.delete(rel)
        await self.db.commit()

    async def get_executives_for_assistant(
        self, tenant_id: uuid.UUID, assistant_extension_id: uuid.UUID
    ) -> list[BossAdminRelationship]:
        return await self.list_relationships(
            tenant_id, assistant_id=assistant_extension_id
        )

    async def get_assistants_for_executive(
        self, tenant_id: uuid.UUID, executive_extension_id: uuid.UUID
    ) -> list[BossAdminRelationship]:
        return await self.list_relationships(
            tenant_id, executive_id=executive_extension_id
        )

    async def validate_extensions(
        self,
        tenant_id: uuid.UUID,
        executive_id: uuid.UUID,
        assistant_id: uuid.UUID,
    ) -> None:
        if executive_id == assistant_id:
            raise ValueError("Executive and assistant must be different extensions")

        exec_result = await self.db.execute(
            select(Extension).where(
                Extension.id == executive_id,
                Extension.tenant_id == tenant_id,
            )
        )
        if not exec_result.scalar_one_or_none():
            raise ValueError("Executive extension not found in this tenant")

        asst_result = await self.db.execute(
            select(Extension).where(
                Extension.id == assistant_id,
                Extension.tenant_id == tenant_id,
            )
        )
        if not asst_result.scalar_one_or_none():
            raise ValueError("Assistant extension not found in this tenant")
