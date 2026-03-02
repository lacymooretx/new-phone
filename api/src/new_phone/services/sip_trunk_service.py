import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.db.rls import set_tenant_context
from new_phone.models.sip_trunk import SIPTrunk
from new_phone.schemas.sip_trunk import SIPTrunkCreate, SIPTrunkUpdate


class SIPTrunkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_trunks(self, tenant_id: uuid.UUID) -> list[SIPTrunk]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SIPTrunk)
            .where(SIPTrunk.tenant_id == tenant_id, SIPTrunk.is_active.is_(True))
            .order_by(SIPTrunk.name)
        )
        return list(result.scalars().all())

    async def get_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> SIPTrunk | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SIPTrunk).where(
                SIPTrunk.id == trunk_id, SIPTrunk.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_trunk(
        self, tenant_id: uuid.UUID, data: SIPTrunkCreate
    ) -> SIPTrunk:
        await set_tenant_context(self.db, tenant_id)
        trunk_data = data.model_dump(exclude={"password"})

        # Encrypt password if provided
        encrypted_pw = None
        if data.password:
            encrypted_pw = encrypt_value(data.password)

        trunk = SIPTrunk(
            tenant_id=tenant_id,
            encrypted_password=encrypted_pw,
            **trunk_data,
        )
        self.db.add(trunk)
        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk

    async def update_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID, data: SIPTrunkUpdate
    ) -> SIPTrunk:
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})
        for key, value in update_data.items():
            setattr(trunk, key, value)

        # Handle password separately — encrypt it
        if data.password is not None:
            trunk.encrypted_password = encrypt_value(data.password)

        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk

    async def deactivate_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> SIPTrunk:
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        trunk.is_active = False
        trunk.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk
