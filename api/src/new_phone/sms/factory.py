import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value
from new_phone.models.sms import SMSProvider, SMSProviderConfig
from new_phone.sms.clearlyip import ClearlyIPProvider
from new_phone.sms.provider_base import SMSProviderBase
from new_phone.sms.twilio import TwilioProvider

logger = structlog.get_logger()


def get_provider(config: SMSProviderConfig) -> SMSProviderBase:
    """Decrypt credentials and return the appropriate provider instance."""
    try:
        creds = json.loads(decrypt_value(config.encrypted_credentials))
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("sms_provider_decrypt_failed", config_id=str(config.id), error=str(e))
        raise ValueError(f"Failed to decrypt SMS provider credentials for config {config.id}") from e

    if config.provider_type == SMSProvider.CLEARLYIP:
        return ClearlyIPProvider(trunk_token=creds["trunk_token"])

    if config.provider_type == SMSProvider.TWILIO:
        return TwilioProvider(
            account_sid=creds["account_sid"],
            auth_token=creds["auth_token"],
        )

    raise ValueError(f"Unknown SMS provider type: {config.provider_type}")


async def get_tenant_default_provider(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[SMSProviderConfig, SMSProviderBase]:
    """Load the default SMS provider config for a tenant and return (config, provider)."""
    result = await db.execute(
        select(SMSProviderConfig).where(
            SMSProviderConfig.tenant_id == tenant_id,
            SMSProviderConfig.is_default.is_(True),
            SMSProviderConfig.is_active.is_(True),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise ValueError(f"No default SMS provider configured for tenant {tenant_id}")

    return config, get_provider(config)
