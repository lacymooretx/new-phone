import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.parking_lot import ParkingLot
from new_phone.schemas.parking_lot import ParkingLotCreate, ParkingLotUpdate, SlotState

logger = structlog.get_logger()


class ParkingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_lots(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[ParkingLot]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(ParkingLot)
            .where(ParkingLot.tenant_id == tenant_id, ParkingLot.is_active.is_(True))
            .order_by(ParkingLot.lot_number)
        )
        if site_id is not None:
            stmt = stmt.where(ParkingLot.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_lot(self, tenant_id: uuid.UUID, lot_id: uuid.UUID) -> ParkingLot | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ParkingLot).where(
                ParkingLot.id == lot_id,
                ParkingLot.tenant_id == tenant_id,
                ParkingLot.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_lot(self, tenant_id: uuid.UUID, data: ParkingLotCreate) -> ParkingLot:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate lot_number
        existing = await self.db.execute(
            select(ParkingLot).where(
                ParkingLot.tenant_id == tenant_id,
                ParkingLot.lot_number == data.lot_number,
                ParkingLot.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Parking lot number {data.lot_number} already exists")

        # Check duplicate name
        existing = await self.db.execute(
            select(ParkingLot).where(
                ParkingLot.tenant_id == tenant_id,
                ParkingLot.name == data.name,
                ParkingLot.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Parking lot '{data.name}' already exists")

        # Check for overlapping slot ranges with existing lots
        all_lots = await self.list_lots(tenant_id)
        for lot in all_lots:
            if data.slot_start <= lot.slot_end and data.slot_end >= lot.slot_start:
                raise ValueError(
                    f"Slot range {data.slot_start}-{data.slot_end} overlaps with "
                    f"lot '{lot.name}' ({lot.slot_start}-{lot.slot_end})"
                )

        parking_lot = ParkingLot(
            tenant_id=tenant_id,
            name=data.name,
            lot_number=data.lot_number,
            slot_start=data.slot_start,
            slot_end=data.slot_end,
            timeout_seconds=data.timeout_seconds,
            comeback_enabled=data.comeback_enabled,
            comeback_extension=data.comeback_extension,
            moh_prompt_id=data.moh_prompt_id,
        )
        self.db.add(parking_lot)
        await self.db.commit()
        await self.db.refresh(parking_lot)
        return parking_lot

    async def update_lot(
        self, tenant_id: uuid.UUID, lot_id: uuid.UUID, data: ParkingLotUpdate
    ) -> ParkingLot:
        lot = await self.get_lot(tenant_id, lot_id)
        if not lot:
            raise ValueError("Parking lot not found")

        update_data = data.model_dump(exclude_unset=True)

        # Check lot_number uniqueness if changing
        if "lot_number" in update_data and update_data["lot_number"] != lot.lot_number:
            existing = await self.db.execute(
                select(ParkingLot).where(
                    ParkingLot.tenant_id == tenant_id,
                    ParkingLot.lot_number == update_data["lot_number"],
                    ParkingLot.is_active.is_(True),
                    ParkingLot.id != lot_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Parking lot number {update_data['lot_number']} already exists")

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != lot.name:
            existing = await self.db.execute(
                select(ParkingLot).where(
                    ParkingLot.tenant_id == tenant_id,
                    ParkingLot.name == update_data["name"],
                    ParkingLot.is_active.is_(True),
                    ParkingLot.id != lot_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Parking lot '{update_data['name']}' already exists")

        # Check slot range overlap if changing
        new_start = update_data.get("slot_start", lot.slot_start)
        new_end = update_data.get("slot_end", lot.slot_end)
        if new_start != lot.slot_start or new_end != lot.slot_end:
            all_lots = await self.list_lots(tenant_id)
            for other in all_lots:
                if other.id == lot_id:
                    continue
                if new_start <= other.slot_end and new_end >= other.slot_start:
                    raise ValueError(
                        f"Slot range {new_start}-{new_end} overlaps with "
                        f"lot '{other.name}' ({other.slot_start}-{other.slot_end})"
                    )

        for key, value in update_data.items():
            setattr(lot, key, value)

        await self.db.commit()
        await self.db.refresh(lot)
        return lot

    async def deactivate(self, tenant_id: uuid.UUID, lot_id: uuid.UUID) -> ParkingLot:
        lot = await self.get_lot(tenant_id, lot_id)
        if not lot:
            raise ValueError("Parking lot not found")
        lot.is_active = False
        await self.db.commit()
        await self.db.refresh(lot)
        return lot

    @staticmethod
    async def get_slot_states(tenant_id: uuid.UUID) -> list[SlotState]:
        """Get all occupied parking slots for a tenant from Redis."""
        from new_phone.main import redis_client

        if not redis_client:
            return []

        pattern = f"parking_slot:{tenant_id}:*"
        slots: list[SlotState] = []
        async for key in redis_client.scan_iter(match=pattern, count=100):
            raw = await redis_client.get(key)
            if raw:
                data = json.loads(raw)
                slots.append(SlotState(**data))
        return sorted(slots, key=lambda s: s.slot_number)

    @staticmethod
    async def get_lot_slot_states(
        tenant_id: uuid.UUID, lot: ParkingLot
    ) -> list[SlotState]:
        """Get full slot grid (occupied + empty) for a single parking lot."""
        from new_phone.main import redis_client

        occupied: dict[int, SlotState] = {}
        if redis_client:
            for slot_num in range(lot.slot_start, lot.slot_end + 1):
                key = f"parking_slot:{tenant_id}:{slot_num}"
                raw = await redis_client.get(key)
                if raw:
                    data = json.loads(raw)
                    occupied[slot_num] = SlotState(**data)

        grid: list[SlotState] = []
        for slot_num in range(lot.slot_start, lot.slot_end + 1):
            if slot_num in occupied:
                grid.append(occupied[slot_num])
            else:
                grid.append(SlotState(
                    slot_number=slot_num,
                    occupied=False,
                    lot_name=lot.name,
                    lot_id=str(lot.id),
                ))
        return grid
