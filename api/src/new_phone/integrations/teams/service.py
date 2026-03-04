"""Microsoft Teams integration service."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.integrations.teams.models import TeamsConfig, TeamsPresenceMapping
from new_phone.integrations.teams.schemas import (
    TeamsConfigCreate,
    TeamsConfigUpdate,
    TeamsPresenceMappingCreate,
)

logger = structlog.get_logger()


class TeamsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Config CRUD -----------------------------------------------------------

    async def get_config(self, tenant_id: uuid.UUID) -> TeamsConfig | None:
        result = await self.db.execute(
            select(TeamsConfig).where(TeamsConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, tenant_id: uuid.UUID, data: TeamsConfigCreate
    ) -> TeamsConfig:
        existing = await self.get_config(tenant_id)
        if existing:
            raise ValueError("Teams integration already configured for this tenant")

        config = TeamsConfig(
            tenant_id=tenant_id,
            azure_tenant_id=data.azure_tenant_id,
            client_id=data.client_id,
            encrypted_client_secret=encrypt_value(data.client_secret),
            presence_sync_enabled=data.presence_sync_enabled,
            direct_routing_enabled=data.direct_routing_enabled,
            bot_app_id=data.bot_app_id,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(
        self, config_id: uuid.UUID, data: TeamsConfigUpdate
    ) -> TeamsConfig:
        result = await self.db.execute(
            select(TeamsConfig).where(TeamsConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Teams config not found")

        update_data = data.model_dump(exclude_unset=True)

        # Handle client_secret separately — re-encrypt if provided
        client_secret = update_data.pop("client_secret", None)
        if client_secret is not None:
            config.encrypted_client_secret = encrypt_value(client_secret)

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(TeamsConfig).where(TeamsConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Teams config not found")
        await self.db.delete(config)
        await self.db.commit()

    # -- Presence Mappings -----------------------------------------------------

    async def list_presence_mappings(
        self, tenant_id: uuid.UUID
    ) -> list[TeamsPresenceMapping]:
        result = await self.db.execute(
            select(TeamsPresenceMapping).where(
                TeamsPresenceMapping.tenant_id == tenant_id
            )
        )
        return list(result.scalars().all())

    async def create_presence_mapping(
        self, tenant_id: uuid.UUID, data: TeamsPresenceMappingCreate
    ) -> TeamsPresenceMapping:
        config = await self.get_config(tenant_id)
        if not config:
            raise ValueError("Teams integration not configured for this tenant")
        mapping = TeamsPresenceMapping(
            tenant_id=tenant_id,
            config_id=config.id,
            extension_id=data.extension_id,
            teams_user_id=data.teams_user_id,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def delete_presence_mapping(self, mapping_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(TeamsPresenceMapping).where(TeamsPresenceMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise ValueError("Presence mapping not found")
        await self.db.delete(mapping)
        await self.db.commit()

    # -- Presence Sync (stub) --------------------------------------------------

    async def sync_presence(self, tenant_id: uuid.UUID) -> dict:
        """Sync presence between PBX extensions and Teams users.

        This is a stub — the real implementation would:
        1. Obtain an OAuth2 token using the stored client credentials.
        2. Call Microsoft Graph API /communications/presences for each mapped user.
        3. Compare and update presence states bidirectionally.
        """
        config = await self.get_config(tenant_id)
        if not config:
            raise ValueError("Teams integration not configured")
        if not config.is_active:
            raise ValueError("Teams integration is disabled")

        mappings = await self.list_presence_mappings(tenant_id)
        if not mappings:
            return {"synced": 0, "errors": 0, "message": "No presence mappings configured"}

        logger.info(
            "teams_presence_sync_stub",
            tenant_id=str(tenant_id),
            mapping_count=len(mappings),
        )

        # Stub: in production this would call Graph API and update last_synced_at
        return {
            "synced": 0,
            "errors": 0,
            "message": f"Stub: {len(mappings)} mappings would be synced via Graph API",
        }
