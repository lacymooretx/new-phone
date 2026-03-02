import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.did import DID
from new_phone.schemas.did import DIDCreate, DIDUpdate


class DIDService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_dids(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[DID]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(DID)
            .where(DID.tenant_id == tenant_id, DID.is_active.is_(True))
            .order_by(DID.number)
        )
        if site_id is not None:
            stmt = stmt.where(DID.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_did(self, tenant_id: uuid.UUID, did_id: uuid.UUID) -> DID | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DID).where(DID.id == did_id, DID.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_did(self, tenant_id: uuid.UUID, data: DIDCreate) -> DID:
        await set_tenant_context(self.db, tenant_id)
        # E.164 numbers are globally unique (no tenant scoping)
        existing = await self.db.execute(
            select(DID).where(DID.number == data.number)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"DID '{data.number}' already exists")

        did = DID(tenant_id=tenant_id, **data.model_dump())
        self.db.add(did)
        await self.db.commit()
        await self.db.refresh(did)
        return did

    async def update_did(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID, data: DIDUpdate
    ) -> DID:
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(did, key, value)

        await self.db.commit()
        await self.db.refresh(did)
        return did

    async def deactivate_did(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID
    ) -> DID:
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        did.is_active = False
        did.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(did)
        return did
