import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.conference_bridge import ConferenceBridge
from new_phone.schemas.conference_bridge import ConferenceBridgeCreate, ConferenceBridgeUpdate

logger = structlog.get_logger()


class ConferenceBridgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bridges(self, tenant_id: uuid.UUID) -> list[ConferenceBridge]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ConferenceBridge)
            .where(ConferenceBridge.tenant_id == tenant_id, ConferenceBridge.is_active.is_(True))
            .order_by(ConferenceBridge.name)
        )
        return list(result.scalars().all())

    async def get_bridge(self, tenant_id: uuid.UUID, bridge_id: uuid.UUID) -> ConferenceBridge | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ConferenceBridge)
            .where(
                ConferenceBridge.id == bridge_id,
                ConferenceBridge.tenant_id == tenant_id,
                ConferenceBridge.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_bridge(self, tenant_id: uuid.UUID, data: ConferenceBridgeCreate) -> ConferenceBridge:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate name
        existing = await self.db.execute(
            select(ConferenceBridge).where(
                ConferenceBridge.tenant_id == tenant_id,
                ConferenceBridge.name == data.name,
                ConferenceBridge.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Conference bridge '{data.name}' already exists")

        # Check duplicate room_number
        existing = await self.db.execute(
            select(ConferenceBridge).where(
                ConferenceBridge.tenant_id == tenant_id,
                ConferenceBridge.room_number == data.room_number,
                ConferenceBridge.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Room number '{data.room_number}' already exists")

        bridge = ConferenceBridge(
            tenant_id=tenant_id,
            name=data.name,
            room_number=data.room_number,
            description=data.description,
            max_participants=data.max_participants,
            participant_pin=data.participant_pin,
            moderator_pin=data.moderator_pin,
            wait_for_moderator=data.wait_for_moderator,
            announce_join_leave=data.announce_join_leave,
            moh_prompt_id=data.moh_prompt_id,
            record_conference=data.record_conference,
            muted_on_join=data.muted_on_join,
            enabled=data.enabled,
        )
        self.db.add(bridge)
        await self.db.commit()
        await self.db.refresh(bridge)
        return bridge

    async def update_bridge(
        self, tenant_id: uuid.UUID, bridge_id: uuid.UUID, data: ConferenceBridgeUpdate
    ) -> ConferenceBridge:
        bridge = await self.get_bridge(tenant_id, bridge_id)
        if not bridge:
            raise ValueError("Conference bridge not found")

        update_data = data.model_dump(exclude_unset=True)

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != bridge.name:
            existing = await self.db.execute(
                select(ConferenceBridge).where(
                    ConferenceBridge.tenant_id == tenant_id,
                    ConferenceBridge.name == update_data["name"],
                    ConferenceBridge.is_active.is_(True),
                    ConferenceBridge.id != bridge_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Conference bridge '{update_data['name']}' already exists")

        # Check room_number uniqueness if changing
        if "room_number" in update_data and update_data["room_number"] != bridge.room_number:
            existing = await self.db.execute(
                select(ConferenceBridge).where(
                    ConferenceBridge.tenant_id == tenant_id,
                    ConferenceBridge.room_number == update_data["room_number"],
                    ConferenceBridge.is_active.is_(True),
                    ConferenceBridge.id != bridge_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Room number '{update_data['room_number']}' already exists")

        for key, value in update_data.items():
            setattr(bridge, key, value)

        await self.db.commit()
        await self.db.refresh(bridge)
        return bridge

    async def deactivate(self, tenant_id: uuid.UUID, bridge_id: uuid.UUID) -> ConferenceBridge:
        bridge = await self.get_bridge(tenant_id, bridge_id)
        if not bridge:
            raise ValueError("Conference bridge not found")
        bridge.is_active = False
        await self.db.commit()
        await self.db.refresh(bridge)
        return bridge
