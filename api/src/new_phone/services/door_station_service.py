import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.door_station import DoorAccessLog, DoorStation
from new_phone.models.extension import Extension
from new_phone.schemas.door_station import DoorStationCreate, DoorStationUpdate

logger = structlog.get_logger()


class DoorStationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_door_stations(self, tenant_id: uuid.UUID) -> list[DoorStation]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DoorStation)
            .where(DoorStation.tenant_id == tenant_id, DoorStation.is_active.is_(True))
            .order_by(DoorStation.name)
        )
        return list(result.scalars().all())

    async def get_door_station(
        self, tenant_id: uuid.UUID, door_station_id: uuid.UUID
    ) -> DoorStation | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DoorStation).where(
                DoorStation.id == door_station_id,
                DoorStation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_door_station(
        self, tenant_id: uuid.UUID, data: DoorStationCreate
    ) -> DoorStation:
        await set_tenant_context(self.db, tenant_id)

        # Validate extension exists
        ext_result = await self.db.execute(
            select(Extension).where(
                Extension.id == data.extension_id,
                Extension.tenant_id == tenant_id,
            )
        )
        if not ext_result.scalar_one_or_none():
            raise ValueError("Extension not found")

        door_station = DoorStation(tenant_id=tenant_id, **data.model_dump())
        self.db.add(door_station)
        await self.db.commit()
        await self.db.refresh(door_station)
        return door_station

    async def update_door_station(
        self, tenant_id: uuid.UUID, door_station_id: uuid.UUID, data: DoorStationUpdate
    ) -> DoorStation:
        door_station = await self.get_door_station(tenant_id, door_station_id)
        if not door_station:
            raise ValueError("Door station not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(door_station, key, value)
        await self.db.commit()
        await self.db.refresh(door_station)
        return door_station

    async def deactivate_door_station(
        self, tenant_id: uuid.UUID, door_station_id: uuid.UUID
    ) -> DoorStation:
        door_station = await self.get_door_station(tenant_id, door_station_id)
        if not door_station:
            raise ValueError("Door station not found")
        door_station.is_active = False
        await self.db.commit()
        await self.db.refresh(door_station)
        return door_station

    async def trigger_unlock(
        self, tenant_id: uuid.UUID, door_station_id: uuid.UUID, user_id: uuid.UUID
    ) -> DoorAccessLog:
        await set_tenant_context(self.db, tenant_id)
        door_station = await self.get_door_station(tenant_id, door_station_id)
        if not door_station:
            raise ValueError("Door station not found")
        if not door_station.unlock_url:
            raise ValueError("Door station has no unlock URL configured")

        # Send HTTP request to unlock door
        unlocked = False
        try:
            import httpx

            headers = door_station.unlock_headers or {}
            async with httpx.AsyncClient(timeout=10) as client:
                method = (door_station.unlock_http_method or "POST").upper()
                if method == "GET":
                    resp = await client.get(door_station.unlock_url, headers=headers)
                elif method == "PUT":
                    resp = await client.put(
                        door_station.unlock_url, headers=headers, content=door_station.unlock_body
                    )
                else:
                    resp = await client.post(
                        door_station.unlock_url, headers=headers, content=door_station.unlock_body
                    )
                unlocked = resp.status_code < 400
                logger.info(
                    "door_unlock_request",
                    door_station_id=str(door_station_id),
                    status=resp.status_code,
                    unlocked=unlocked,
                )
        except Exception as e:
            logger.error("door_unlock_failed", door_station_id=str(door_station_id), error=str(e))

        # Log access
        log_entry = DoorAccessLog(
            tenant_id=tenant_id,
            door_station_id=door_station_id,
            door_unlocked=unlocked,
            unlocked_by_user_id=user_id,
            unlock_triggered_at=datetime.now(UTC) if unlocked else None,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def list_access_logs(
        self, tenant_id: uuid.UUID, door_station_id: uuid.UUID, limit: int = 50
    ) -> list[DoorAccessLog]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DoorAccessLog)
            .where(
                DoorAccessLog.door_station_id == door_station_id,
                DoorAccessLog.tenant_id == tenant_id,
            )
            .order_by(DoorAccessLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
