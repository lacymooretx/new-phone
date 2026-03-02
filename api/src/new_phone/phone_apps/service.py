from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.phone_app_config import PhoneAppConfig
from new_phone.schemas.phone_app_config import PhoneAppConfigUpdate


class PhoneAppConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, tenant_id: uuid.UUID) -> PhoneAppConfig:
        """Return existing config or create default for tenant."""
        result = await self.db.execute(
            select(PhoneAppConfig).where(PhoneAppConfig.tenant_id == tenant_id)
        )
        config = result.scalar_one_or_none()
        if config:
            return config

        config = PhoneAppConfig(tenant_id=tenant_id)
        self.db.add(config)
        await self.db.flush()
        return config

    async def get(self, tenant_id: uuid.UUID) -> PhoneAppConfig | None:
        result = await self.db.execute(
            select(PhoneAppConfig).where(PhoneAppConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update(self, tenant_id: uuid.UUID, data: PhoneAppConfigUpdate) -> PhoneAppConfig:
        config = await self.get_or_create(tenant_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
        await self.db.flush()
        return config
