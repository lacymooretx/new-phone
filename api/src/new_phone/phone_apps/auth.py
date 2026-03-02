"""MAC-based phone authentication — same pattern as provisioning/router.py."""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog
from sqlalchemy import select

from new_phone.db.engine import AdminSessionLocal
from new_phone.models.device import Device
from new_phone.models.extension import Extension
from new_phone.models.phone_model import PhoneModel
from new_phone.models.tenant import Tenant
from new_phone.services.device_service import DeviceService

logger = structlog.get_logger()

MAC_RE = re.compile(r"^[0-9a-fA-F]{12}$")

# Canonical manufacturer slugs used for renderer dispatch
_MANUFACTURER_SLUGS = {
    "yealink": "yealink",
    "polycom": "polycom",
    "poly": "polycom",
    "cisco": "cisco",
}


@dataclass(frozen=True)
class PhoneContext:
    device: Device
    extension: Extension
    tenant: Tenant
    phone_model: PhoneModel
    mac: str
    manufacturer: str  # "yealink" | "polycom" | "cisco"


async def resolve_phone_context(mac: str) -> PhoneContext | None:
    """Resolve MAC → device → extension → tenant → manufacturer.

    Returns None if any required entity is missing.
    Uses AdminSessionLocal (no RLS) — same as provisioning.
    """
    if not MAC_RE.match(mac):
        logger.debug("phone_apps_invalid_mac", mac=mac)
        return None

    mac = mac.lower()

    async with AdminSessionLocal() as session:
        service = DeviceService(session)
        device = await service.get_device_by_mac(mac)
        if not device:
            logger.debug("phone_apps_device_not_found", mac=mac)
            return None

        # Must have an assigned extension
        if not device.extension_id:
            logger.debug("phone_apps_no_extension", mac=mac)
            return None

        # Load phone model
        result = await session.execute(
            select(PhoneModel).where(PhoneModel.id == device.phone_model_id)
        )
        phone_model = result.scalar_one_or_none()
        if not phone_model:
            logger.error("phone_apps_model_not_found", device_id=str(device.id))
            return None

        # Load tenant
        result = await session.execute(select(Tenant).where(Tenant.id == device.tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.error("phone_apps_tenant_not_found", device_id=str(device.id))
            return None

        # Load extension
        result = await session.execute(select(Extension).where(Extension.id == device.extension_id))
        extension = result.scalar_one_or_none()
        if not extension:
            logger.error("phone_apps_extension_not_found", device_id=str(device.id))
            return None

        # Determine manufacturer slug (default to yealink)
        raw_mfr = phone_model.manufacturer.lower().strip()
        manufacturer = _MANUFACTURER_SLUGS.get(raw_mfr, "yealink")

        return PhoneContext(
            device=device,
            extension=extension,
            tenant=tenant,
            phone_model=phone_model,
            mac=mac,
            manufacturer=manufacturer,
        )
