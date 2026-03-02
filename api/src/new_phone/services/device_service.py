import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.device import Device, DeviceKey
from new_phone.schemas.device import DeviceCreate, DeviceKeyCreate, DeviceUpdate, _normalize_mac


class DeviceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_devices(self, tenant_id: uuid.UUID) -> list[Device]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Device)
            .where(Device.tenant_id == tenant_id, Device.is_active.is_(True))
            .order_by(Device.name)
        )
        return list(result.unique().scalars().all())

    async def get_device(self, tenant_id: uuid.UUID, device_id: uuid.UUID) -> Device | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Device).where(
                Device.id == device_id, Device.tenant_id == tenant_id
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_device_by_mac(self, mac_address: str) -> Device | None:
        """Lookup device by MAC — uses admin session, no tenant context needed."""
        normalized = _normalize_mac(mac_address)
        result = await self.db.execute(
            select(Device).where(
                Device.mac_address == normalized,
                Device.is_active.is_(True),
                Device.provisioning_enabled.is_(True),
            )
        )
        return result.unique().scalar_one_or_none()

    async def create_device(self, tenant_id: uuid.UUID, data: DeviceCreate) -> Device:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate MAC globally (unique across all tenants)
        existing = await self.db.execute(
            select(Device).where(Device.mac_address == data.mac_address)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"MAC address '{data.mac_address}' is already registered")

        device = Device(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def update_device(
        self, tenant_id: uuid.UUID, device_id: uuid.UUID, data: DeviceUpdate
    ) -> Device:
        device = await self.get_device(tenant_id, device_id)
        if not device:
            raise ValueError("Device not found")

        update_data = data.model_dump(exclude_unset=True)

        # If MAC is being changed, check for duplicates
        if "mac_address" in update_data and update_data["mac_address"] != device.mac_address:
            existing = await self.db.execute(
                select(Device).where(Device.mac_address == update_data["mac_address"])
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"MAC address '{update_data['mac_address']}' is already registered")

        for key, value in update_data.items():
            setattr(device, key, value)

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def deactivate_device(
        self, tenant_id: uuid.UUID, device_id: uuid.UUID
    ) -> Device:
        device = await self.get_device(tenant_id, device_id)
        if not device:
            raise ValueError("Device not found")

        device.is_active = False
        device.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def get_device_keys(
        self, tenant_id: uuid.UUID, device_id: uuid.UUID
    ) -> list[DeviceKey]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DeviceKey)
            .where(DeviceKey.device_id == device_id, DeviceKey.tenant_id == tenant_id)
            .order_by(DeviceKey.key_section, DeviceKey.key_index)
        )
        return list(result.scalars().all())

    async def bulk_update_keys(
        self, tenant_id: uuid.UUID, device_id: uuid.UUID, keys: list[DeviceKeyCreate]
    ) -> list[DeviceKey]:
        await set_tenant_context(self.db, tenant_id)

        # Verify device exists
        device = await self.get_device(tenant_id, device_id)
        if not device:
            raise ValueError("Device not found")

        # Delete existing keys
        existing = await self.db.execute(
            select(DeviceKey).where(
                DeviceKey.device_id == device_id,
                DeviceKey.tenant_id == tenant_id,
            )
        )
        for key in existing.scalars().all():
            await self.db.delete(key)

        # Insert new keys
        new_keys = []
        for key_data in keys:
            dk = DeviceKey(
                tenant_id=tenant_id,
                device_id=device_id,
                **key_data.model_dump(),
            )
            self.db.add(dk)
            new_keys.append(dk)

        await self.db.commit()

        # Refresh all
        for dk in new_keys:
            await self.db.refresh(dk)

        return new_keys

    async def stamp_provisioned(self, device: Device, config_hash: str) -> None:
        """Update provisioning timestamp and config hash (admin session)."""
        device.last_provisioned_at = datetime.now(UTC)
        device.last_config_hash = config_hash
        await self.db.commit()
