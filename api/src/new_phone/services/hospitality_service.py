import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.hospitality import HousekeepingStatus, Room, RoomStatus, WakeUpCall
from new_phone.schemas.hospitality import RoomCreate, RoomUpdate

logger = structlog.get_logger()


class HospitalityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rooms(
        self,
        tenant_id: uuid.UUID,
        *,
        status: str | None = None,
        floor: str | None = None,
    ) -> list[Room]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(Room)
            .where(Room.tenant_id == tenant_id)
            .order_by(Room.room_number)
        )
        if status is not None:
            stmt = stmt.where(Room.status == status)
        if floor is not None:
            stmt = stmt.where(Room.floor == floor)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_room(self, tenant_id: uuid.UUID, room_id: uuid.UUID) -> Room | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Room).where(
                Room.id == room_id,
                Room.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_room(self, tenant_id: uuid.UUID, data: RoomCreate) -> Room:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate room_number
        existing = await self.db.execute(
            select(Room).where(
                Room.tenant_id == tenant_id,
                Room.room_number == data.room_number,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Room number {data.room_number} already exists")

        room = Room(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(room)
        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def update_room(
        self, tenant_id: uuid.UUID, room_id: uuid.UUID, data: RoomUpdate
    ) -> Room:
        room = await self.get_room(tenant_id, room_id)
        if not room:
            raise ValueError("Room not found")

        update_data = data.model_dump(exclude_unset=True)

        # Check room_number uniqueness if changing
        if "room_number" in update_data and update_data["room_number"] != room.room_number:
            existing = await self.db.execute(
                select(Room).where(
                    Room.tenant_id == tenant_id,
                    Room.room_number == update_data["room_number"],
                    Room.id != room_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Room number {update_data['room_number']} already exists")

        for key, value in update_data.items():
            setattr(room, key, value)

        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def check_in(
        self,
        tenant_id: uuid.UUID,
        room_id: uuid.UUID,
        guest_name: str,
        guest_checkout_at: datetime | None = None,
    ) -> Room:
        room = await self.get_room(tenant_id, room_id)
        if not room:
            raise ValueError("Room not found")

        room.status = RoomStatus.OCCUPIED
        room.guest_name = guest_name
        room.guest_checkout_at = guest_checkout_at
        room.housekeeping_status = HousekeepingStatus.CLEAN
        room.restricted_dialing = False

        await self.db.commit()
        await self.db.refresh(room)
        logger.info("room_checked_in", room_id=str(room_id), guest_name=guest_name)
        return room

    async def check_out(self, tenant_id: uuid.UUID, room_id: uuid.UUID) -> Room:
        room = await self.get_room(tenant_id, room_id)
        if not room:
            raise ValueError("Room not found")

        # Reset guest info and phone settings
        room.status = RoomStatus.VACANT
        room.guest_name = None
        room.guest_checkout_at = None
        room.wake_up_time = None
        room.wake_up_enabled = False
        room.restricted_dialing = True
        room.housekeeping_status = HousekeepingStatus.DIRTY
        room.notes = None

        # Cancel any pending wake-up calls
        pending_calls = await self.db.execute(
            select(WakeUpCall).where(
                WakeUpCall.room_id == room_id,
                WakeUpCall.tenant_id == tenant_id,
                WakeUpCall.status == "pending",
            )
        )
        for call in pending_calls.scalars().all():
            call.status = "cancelled"

        await self.db.commit()
        await self.db.refresh(room)
        logger.info("room_checked_out", room_id=str(room_id))
        return room

    # --- Wake-up calls ---

    async def list_wake_up_calls(
        self, tenant_id: uuid.UUID, room_id: uuid.UUID
    ) -> list[WakeUpCall]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WakeUpCall)
            .where(
                WakeUpCall.tenant_id == tenant_id,
                WakeUpCall.room_id == room_id,
            )
            .order_by(WakeUpCall.scheduled_time)
        )
        return list(result.scalars().all())

    async def create_wake_up_call(
        self, tenant_id: uuid.UUID, room_id: uuid.UUID, scheduled_time: datetime
    ) -> WakeUpCall:
        await set_tenant_context(self.db, tenant_id)

        # Verify room exists
        room = await self.get_room(tenant_id, room_id)
        if not room:
            raise ValueError("Room not found")

        wake_up = WakeUpCall(
            tenant_id=tenant_id,
            room_id=room_id,
            scheduled_time=scheduled_time,
            status="pending",
        )
        self.db.add(wake_up)
        await self.db.commit()
        await self.db.refresh(wake_up)
        logger.info("wake_up_call_created", room_id=str(room_id), scheduled_time=str(scheduled_time))
        return wake_up

    async def cancel_wake_up_call(
        self, tenant_id: uuid.UUID, wake_up_id: uuid.UUID
    ) -> WakeUpCall:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WakeUpCall).where(
                WakeUpCall.id == wake_up_id,
                WakeUpCall.tenant_id == tenant_id,
            )
        )
        wake_up = result.scalar_one_or_none()
        if not wake_up:
            raise ValueError("Wake-up call not found")

        wake_up.status = "cancelled"
        await self.db.commit()
        await self.db.refresh(wake_up)
        logger.info("wake_up_call_cancelled", wake_up_id=str(wake_up_id))
        return wake_up
