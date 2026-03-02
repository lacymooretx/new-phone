import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.disposition import DispositionCode, DispositionCodeList
from new_phone.schemas.disposition import (
    DispositionCodeCreate,
    DispositionCodeListCreate,
    DispositionCodeListUpdate,
    DispositionCodeUpdate,
)


class DispositionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Code Lists ──

    async def list_code_lists(self, tenant_id: uuid.UUID) -> list[DispositionCodeList]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DispositionCodeList)
            .where(
                DispositionCodeList.tenant_id == tenant_id,
                DispositionCodeList.is_active.is_(True),
            )
            .order_by(DispositionCodeList.name)
        )
        return list(result.scalars().unique().all())

    async def get_code_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID
    ) -> DispositionCodeList | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DispositionCodeList).where(
                DispositionCodeList.id == list_id,
                DispositionCodeList.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_code_list(
        self, tenant_id: uuid.UUID, data: DispositionCodeListCreate
    ) -> DispositionCodeList:
        await set_tenant_context(self.db, tenant_id)
        code_list = DispositionCodeList(tenant_id=tenant_id, **data.model_dump())
        self.db.add(code_list)
        await self.db.commit()
        await self.db.refresh(code_list)
        return code_list

    async def update_code_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID, data: DispositionCodeListUpdate
    ) -> DispositionCodeList:
        code_list = await self.get_code_list(tenant_id, list_id)
        if not code_list:
            raise ValueError("Disposition code list not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(code_list, key, value)
        await self.db.commit()
        await self.db.refresh(code_list)
        return code_list

    async def deactivate_code_list(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID
    ) -> DispositionCodeList:
        code_list = await self.get_code_list(tenant_id, list_id)
        if not code_list:
            raise ValueError("Disposition code list not found")
        code_list.is_active = False
        await self.db.commit()
        await self.db.refresh(code_list)
        return code_list

    # ── Codes ──

    async def create_code(
        self, tenant_id: uuid.UUID, list_id: uuid.UUID, data: DispositionCodeCreate
    ) -> DispositionCode:
        await set_tenant_context(self.db, tenant_id)
        # Verify list belongs to tenant
        code_list = await self.get_code_list(tenant_id, list_id)
        if not code_list:
            raise ValueError("Disposition code list not found")
        # Check uniqueness
        existing = await self.db.execute(
            select(DispositionCode).where(
                DispositionCode.list_id == list_id,
                DispositionCode.code == data.code,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Code '{data.code}' already exists in this list")
        code = DispositionCode(tenant_id=tenant_id, list_id=list_id, **data.model_dump())
        self.db.add(code)
        await self.db.commit()
        await self.db.refresh(code)
        return code

    async def get_code(
        self, tenant_id: uuid.UUID, code_id: uuid.UUID
    ) -> DispositionCode | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DispositionCode).where(
                DispositionCode.id == code_id,
                DispositionCode.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_code(
        self, tenant_id: uuid.UUID, code_id: uuid.UUID, data: DispositionCodeUpdate
    ) -> DispositionCode:
        code = await self.get_code(tenant_id, code_id)
        if not code:
            raise ValueError("Disposition code not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(code, key, value)
        await self.db.commit()
        await self.db.refresh(code)
        return code

    async def deactivate_code(
        self, tenant_id: uuid.UUID, code_id: uuid.UUID
    ) -> DispositionCode:
        code = await self.get_code(tenant_id, code_id)
        if not code:
            raise ValueError("Disposition code not found")
        code.is_active = False
        await self.db.commit()
        await self.db.refresh(code)
        return code
