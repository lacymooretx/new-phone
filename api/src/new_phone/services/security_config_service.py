import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.security_config import PanicNotificationTarget, SecurityConfig
from new_phone.schemas.security_config import PanicNotificationTargetCreate, SecurityConfigUpdate


class SecurityConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, tenant_id: uuid.UUID) -> SecurityConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SecurityConfig).where(SecurityConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self, tenant_id: uuid.UUID, data: SecurityConfigUpdate
    ) -> SecurityConfig:
        await set_tenant_context(self.db, tenant_id)
        config = await self.get_config(tenant_id)
        if not config:
            config = SecurityConfig(tenant_id=tenant_id)
            self.db.add(config)
            await self.db.flush()

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def list_notification_targets(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID
    ) -> list[PanicNotificationTarget]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PanicNotificationTarget)
            .where(
                PanicNotificationTarget.security_config_id == config_id,
                PanicNotificationTarget.tenant_id == tenant_id,
            )
            .order_by(PanicNotificationTarget.priority)
        )
        return list(result.scalars().all())

    async def add_notification_target(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID, data: PanicNotificationTargetCreate
    ) -> PanicNotificationTarget:
        await set_tenant_context(self.db, tenant_id)
        # Verify config exists
        config = await self.get_config(tenant_id)
        if not config or str(config.id) != str(config_id):
            raise ValueError("Security config not found")

        target = PanicNotificationTarget(
            tenant_id=tenant_id,
            security_config_id=config_id,
            **data.model_dump(),
        )
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def remove_notification_target(self, tenant_id: uuid.UUID, target_id: uuid.UUID) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PanicNotificationTarget).where(
                PanicNotificationTarget.id == target_id,
                PanicNotificationTarget.tenant_id == tenant_id,
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError("Notification target not found")
        await self.db.delete(target)
        await self.db.commit()
