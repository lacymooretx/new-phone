"""CRM config CRUD service — follows ConnectWiseService pattern."""

import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.integrations.crm.factory import get_crm_provider
from new_phone.models.crm_config import CRMConfig
from new_phone.schemas.crm import CRMConfigCreate, CRMConfigUpdate

logger = structlog.get_logger()


class CRMConfigService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def get_config(self, tenant_id: uuid.UUID) -> CRMConfig | None:
        result = await self.db.execute(select(CRMConfig).where(CRMConfig.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def create_config(self, tenant_id: uuid.UUID, data: CRMConfigCreate) -> CRMConfig:
        existing = await self.get_config(tenant_id)
        if existing:
            raise ValueError("CRM already configured for this tenant")

        config = CRMConfig(
            tenant_id=tenant_id,
            provider_type=data.provider_type,
            encrypted_credentials=encrypt_value(json.dumps(data.credentials)),
            base_url=data.base_url,
            cache_ttl_seconds=data.cache_ttl_seconds,
            lookup_timeout_seconds=data.lookup_timeout_seconds,
            enrichment_enabled=data.enrichment_enabled,
            enrich_inbound=data.enrich_inbound,
            enrich_outbound=data.enrich_outbound,
            custom_fields_map=data.custom_fields_map,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(self, config_id: uuid.UUID, data: CRMConfigUpdate) -> CRMConfig:
        result = await self.db.execute(select(CRMConfig).where(CRMConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("CRM config not found")

        update_data = data.model_dump(exclude_unset=True)

        # Handle credentials separately — re-encrypt if provided
        credentials = update_data.pop("credentials", None)
        if credentials is not None:
            config.encrypted_credentials = encrypt_value(json.dumps(credentials))

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(select(CRMConfig).where(CRMConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("CRM config not found")
        await self.db.delete(config)
        await self.db.commit()

    async def test_connection(self, tenant_id: uuid.UUID) -> dict:
        config = await self.get_config(tenant_id)
        if not config:
            raise ValueError("CRM not configured")

        provider = get_crm_provider(config)
        try:
            return await provider.test_connection()
        finally:
            await provider.close()

    async def invalidate_cache(self, tenant_id: uuid.UUID, phone_number: str | None = None) -> int:
        """Delete CRM lookup cache keys from Redis."""
        if not self.redis:
            return 0

        if phone_number:
            pattern = f"crm:{tenant_id}:{phone_number}"
            deleted = await self.redis.delete(pattern)
            return deleted

        # Scan and delete all keys for this tenant
        pattern = f"crm:{tenant_id}:*"
        keys_deleted = 0
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                keys_deleted += await self.redis.delete(*keys)
            if cursor == 0:
                break
        return keys_deleted
