import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.models.telephony_provider_config import TelephonyProviderConfig
from new_phone.schemas.telephony_provider_config import (
    TelephonyProviderConfigCreate,
    TelephonyProviderConfigUpdate,
)

logger = structlog.get_logger()


class TelephonyProviderConfigService:
    """CRUD + credential resolution for the two-tier telephony provider store."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD (scoped by tenant_id — pass None for MSP-level configs)
    # ------------------------------------------------------------------

    async def list_configs(
        self, tenant_id: uuid.UUID | None
    ) -> list[TelephonyProviderConfig]:
        stmt = (
            select(TelephonyProviderConfig)
            .where(TelephonyProviderConfig.is_active.is_(True))
            .order_by(TelephonyProviderConfig.label)
        )
        if tenant_id is None:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id.is_(None))
        else:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_config(
        self, config_id: uuid.UUID, tenant_id: uuid.UUID | None
    ) -> TelephonyProviderConfig | None:
        stmt = select(TelephonyProviderConfig).where(
            TelephonyProviderConfig.id == config_id,
        )
        if tenant_id is None:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id.is_(None))
        else:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_config(
        self, data: TelephonyProviderConfigCreate, tenant_id: uuid.UUID | None
    ) -> TelephonyProviderConfig:
        if data.is_default:
            await self._unset_defaults(tenant_id, data.provider_type)

        encrypted = encrypt_value(json.dumps(data.credentials))

        config = TelephonyProviderConfig(
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

        logger.info(
            "telephony_provider_config_created",
            config_id=str(config.id),
            tenant_id=str(tenant_id) if tenant_id else "msp",
            provider_type=data.provider_type,
        )
        return config

    async def update_config(
        self,
        config_id: uuid.UUID,
        data: TelephonyProviderConfigUpdate,
        tenant_id: uuid.UUID | None,
    ) -> TelephonyProviderConfig:
        config = await self.get_config(config_id, tenant_id)
        if not config:
            raise ValueError("Telephony provider config not found")

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_default"):
            await self._unset_defaults(tenant_id, config.provider_type)

        if "credentials" in update_data and update_data["credentials"] is not None:
            config.encrypted_credentials = encrypt_value(
                json.dumps(update_data.pop("credentials"))
            )

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)

        logger.info(
            "telephony_provider_config_updated",
            config_id=str(config.id),
            tenant_id=str(tenant_id) if tenant_id else "msp",
        )
        return config

    async def delete_config(
        self, config_id: uuid.UUID, tenant_id: uuid.UUID | None
    ) -> TelephonyProviderConfig:
        config = await self.get_config(config_id, tenant_id)
        if not config:
            raise ValueError("Telephony provider config not found")

        config.is_active = False
        config.is_default = False
        await self.db.commit()
        await self.db.refresh(config)

        logger.info(
            "telephony_provider_config_deleted",
            config_id=str(config.id),
            tenant_id=str(tenant_id) if tenant_id else "msp",
        )
        return config

    # ------------------------------------------------------------------
    # Credential resolution (tenant -> MSP -> None for env fallback)
    # ------------------------------------------------------------------

    async def resolve_credentials(
        self, tenant_id: uuid.UUID, provider_type: str
    ) -> dict | None:
        """Resolve credentials for a tenant+provider using the two-tier hierarchy.

        Returns decrypted credential dict, or None (caller falls back to env vars).
        Resolution: 1) tenant default  2) MSP default  3) None
        """
        # 1. Tenant-level default
        result = await self.db.execute(
            select(TelephonyProviderConfig).where(
                TelephonyProviderConfig.tenant_id == tenant_id,
                TelephonyProviderConfig.provider_type == provider_type,
                TelephonyProviderConfig.is_default.is_(True),
                TelephonyProviderConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()
        if config:
            logger.debug(
                "telephony_creds_resolved",
                source="tenant",
                tenant_id=str(tenant_id),
                provider_type=provider_type,
            )
            return json.loads(decrypt_value(config.encrypted_credentials))

        # 2. MSP-level default
        result = await self.db.execute(
            select(TelephonyProviderConfig).where(
                TelephonyProviderConfig.tenant_id.is_(None),
                TelephonyProviderConfig.provider_type == provider_type,
                TelephonyProviderConfig.is_default.is_(True),
                TelephonyProviderConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()
        if config:
            logger.debug(
                "telephony_creds_resolved",
                source="msp",
                tenant_id=str(tenant_id),
                provider_type=provider_type,
            )
            return json.loads(decrypt_value(config.encrypted_credentials))

        # 3. No DB config — caller should fall back to env vars
        logger.debug(
            "telephony_creds_resolved",
            source="env_var_fallback",
            tenant_id=str(tenant_id),
            provider_type=provider_type,
        )
        return None

    async def get_effective_providers(
        self, tenant_id: uuid.UUID
    ) -> list[dict]:
        """Return effective provider status for each provider type."""
        results = []
        for provider_type in ("clearlyip", "twilio"):
            # Check tenant default
            tenant_result = await self.db.execute(
                select(TelephonyProviderConfig).where(
                    TelephonyProviderConfig.tenant_id == tenant_id,
                    TelephonyProviderConfig.provider_type == provider_type,
                    TelephonyProviderConfig.is_default.is_(True),
                    TelephonyProviderConfig.is_active.is_(True),
                )
            )
            tenant_config = tenant_result.scalar_one_or_none()
            if tenant_config:
                results.append({
                    "provider_type": provider_type,
                    "source": "tenant",
                    "is_configured": True,
                    "label": tenant_config.label,
                    "config_id": tenant_config.id,
                })
                continue

            # Check MSP default
            msp_result = await self.db.execute(
                select(TelephonyProviderConfig).where(
                    TelephonyProviderConfig.tenant_id.is_(None),
                    TelephonyProviderConfig.provider_type == provider_type,
                    TelephonyProviderConfig.is_default.is_(True),
                    TelephonyProviderConfig.is_active.is_(True),
                )
            )
            msp_config = msp_result.scalar_one_or_none()
            if msp_config:
                results.append({
                    "provider_type": provider_type,
                    "source": "msp",
                    "is_configured": True,
                    "label": msp_config.label,
                    "config_id": msp_config.id,
                })
                continue

            # Check env var fallback
            from new_phone.config import settings

            has_env = False
            if provider_type == "clearlyip":
                has_env = bool(settings.clearlyip_keycode)
            elif provider_type == "twilio":
                has_env = bool(settings.twilio_account_sid and settings.twilio_auth_token)

            results.append({
                "provider_type": provider_type,
                "source": "env_var" if has_env else "none",
                "is_configured": has_env,
                "label": None,
                "config_id": None,
            })

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _unset_defaults(
        self, tenant_id: uuid.UUID | None, provider_type: str
    ) -> None:
        """Unset existing defaults for the given scope and provider type."""
        stmt = select(TelephonyProviderConfig).where(
            TelephonyProviderConfig.provider_type == provider_type,
            TelephonyProviderConfig.is_default.is_(True),
        )
        if tenant_id is None:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id.is_(None))
        else:
            stmt = stmt.where(TelephonyProviderConfig.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        for cfg in result.scalars().all():
            cfg.is_default = False
