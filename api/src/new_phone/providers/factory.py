"""Factory for constructing telephony provider instances."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.config import settings
from new_phone.providers.base import TelephonyProvider
from new_phone.providers.clearlyip import ClearlyIPProvider
from new_phone.providers.twilio import TwilioProvider

logger = structlog.get_logger()


def get_provider(provider_type: str, credentials: dict | None = None) -> TelephonyProvider:
    """Return a provider instance for the given type.

    Parameters
    ----------
    provider_type:
        One of ``"clearlyip"`` or ``"twilio"``.
    credentials:
        Optional dict overriding default credentials from config.
        For ClearlyIP: ``{"base_url": ..., "api_key": ...}``
        For Twilio: ``{"account_sid": ..., "auth_token": ...}``
    """
    creds = credentials or {}
    ptype = provider_type.lower()

    if ptype == "clearlyip":
        return ClearlyIPProvider(
            base_url=creds.get("base_url", settings.clearlyip_api_url),
            api_key=creds.get("api_key", settings.clearlyip_api_key),
        )

    if ptype == "twilio":
        return TwilioProvider(
            account_sid=creds.get("account_sid", settings.twilio_account_sid),
            auth_token=creds.get("auth_token", settings.twilio_auth_token),
        )

    raise ValueError(f"Unknown provider type: {provider_type}")


async def get_tenant_provider(
    db: AsyncSession, tenant_id: uuid.UUID
) -> TelephonyProvider:
    """Determine the preferred provider for a tenant and return an instance.

    Current logic:
    1. If the tenant has an active SIP trunk with a ``provider_type`` set, use
       that provider.
    2. Otherwise fall back to ClearlyIP (platform default).
    """
    from new_phone.models.sip_trunk import SIPTrunk

    # Look for an existing trunk with a provider_type
    result = await db.execute(
        select(SIPTrunk).where(
            SIPTrunk.tenant_id == tenant_id,
            SIPTrunk.is_active.is_(True),
            SIPTrunk.provider_type.isnot(None),
        ).order_by(SIPTrunk.created_at).limit(1)
    )
    trunk = result.scalar_one_or_none()
    if trunk and trunk.provider_type:
        logger.debug(
            "tenant_provider_from_trunk",
            tenant_id=str(tenant_id),
            provider_type=trunk.provider_type,
        )
        return get_provider(trunk.provider_type)

    # Default to ClearlyIP
    logger.debug(
        "tenant_provider_default",
        tenant_id=str(tenant_id),
        provider_type="clearlyip",
    )
    return get_provider("clearlyip")
