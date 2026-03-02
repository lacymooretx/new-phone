import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.db.rls import set_tenant_context
from new_phone.models.sms import SMSProviderConfig
from new_phone.schemas.sms import SMSProviderConfigCreate, SMSProviderConfigUpdate

logger = structlog.get_logger()


class SMSProviderConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_configs(self, tenant_id: uuid.UUID) -> list[SMSProviderConfig]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SMSProviderConfig)
            .where(
                SMSProviderConfig.tenant_id == tenant_id,
                SMSProviderConfig.is_active.is_(True),
            )
            .order_by(SMSProviderConfig.label)
        )
        return list(result.scalars().all())

    async def get_config(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID
    ) -> SMSProviderConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SMSProviderConfig).where(
                SMSProviderConfig.id == config_id,
                SMSProviderConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, tenant_id: uuid.UUID, data: SMSProviderConfigCreate
    ) -> SMSProviderConfig:
        await set_tenant_context(self.db, tenant_id)

        # If this is marked as default, unset any existing default
        if data.is_default:
            await self._unset_defaults(tenant_id)

        encrypted = encrypt_value(json.dumps(data.credentials))

        config = SMSProviderConfig(
            tenant_id=tenant_id,
            provider_type=data.provider_type,
            label=data.label,
            encrypted_credentials=encrypted,
            is_default=data.is_default,
            notes=data.notes,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID, data: SMSProviderConfigUpdate
    ) -> SMSProviderConfig:
        config = await self.get_config(tenant_id, config_id)
        if not config:
            raise ValueError("SMS provider config not found")

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_default"):
            await self._unset_defaults(tenant_id)

        if "credentials" in update_data and update_data["credentials"] is not None:
            config.encrypted_credentials = encrypt_value(json.dumps(update_data.pop("credentials")))

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID
    ) -> SMSProviderConfig:
        config = await self.get_config(tenant_id, config_id)
        if not config:
            raise ValueError("SMS provider config not found")

        config.is_active = False
        config.is_default = False
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_default_config(self, tenant_id: uuid.UUID) -> SMSProviderConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SMSProviderConfig).where(
                SMSProviderConfig.tenant_id == tenant_id,
                SMSProviderConfig.is_default.is_(True),
                SMSProviderConfig.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _unset_defaults(self, tenant_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(SMSProviderConfig).where(
                SMSProviderConfig.tenant_id == tenant_id,
                SMSProviderConfig.is_default.is_(True),
            )
        )
        for cfg in result.scalars().all():
            cfg.is_default = False
