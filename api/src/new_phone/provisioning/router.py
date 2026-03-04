"""HTTP provisioning endpoint — unauthenticated, called by phones.

Yealink phones request: GET /provisioning/{mac}.cfg
Sangoma phones request: GET /provisioning/{mac}.xml
The MAC is extracted from the filename, the device is looked up, and
a rendered config is returned.
"""

from __future__ import annotations

import re

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import select

from new_phone.auth.encryption import decrypt_value
from new_phone.config import settings
from new_phone.db.engine import AdminSessionLocal
from new_phone.models.device import DeviceKey
from new_phone.models.extension import Extension
from new_phone.models.phone_model import PhoneModel
from new_phone.models.tenant import Tenant
from new_phone.provisioning.config_builder import build_config, get_content_type
from new_phone.services.device_service import DeviceService

logger = structlog.get_logger()

router = APIRouter(tags=["provisioning"])

# Match MAC from filename: aabbccddeeff.cfg or aabbccddeeff.xml
MAC_PATTERN = re.compile(r"^([0-9a-fA-F]{12})\.(cfg|xml)$")


@router.get("/provisioning/{filename}")
async def provisioning_endpoint(filename: str) -> Response:
    """Serve phone configuration by MAC address.

    Yealink phones request {mac}.cfg, Sangoma phones request {mac}.xml.
    This endpoint is unauthenticated — phones can't send JWTs.
    """
    match = MAC_PATTERN.match(filename)
    if not match:
        return Response(
            content="Invalid filename format",
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="text/plain",
        )

    mac = match.group(1).lower()

    logger.debug("provisioning_request", mac=mac, filename=filename)

    async with AdminSessionLocal() as session:
        # Look up device by MAC (admin session, cross-tenant)
        service = DeviceService(session)
        device = await service.get_device_by_mac(mac)

        if not device:
            logger.debug("provisioning_device_not_found", mac=mac)
            return Response(
                content="Device not registered",
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="text/plain",
            )

        # Load phone model
        result = await session.execute(
            select(PhoneModel).where(PhoneModel.id == device.phone_model_id)
        )
        phone_model = result.scalar_one_or_none()
        if not phone_model:
            logger.error("provisioning_model_not_found", device_id=str(device.id))
            return Response(
                content="Phone model not found",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="text/plain",
            )

        # Load tenant
        result = await session.execute(
            select(Tenant).where(Tenant.id == device.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.error("provisioning_tenant_not_found", device_id=str(device.id))
            return Response(
                content="Tenant not found",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="text/plain",
            )

        # Load extension + decrypt SIP password if assigned
        extension = None
        sip_password = None
        if device.extension_id:
            result = await session.execute(
                select(Extension).where(Extension.id == device.extension_id)
            )
            extension = result.scalar_one_or_none()

            if extension and extension.encrypted_sip_password:
                try:
                    sip_password = decrypt_value(extension.encrypted_sip_password)
                except ValueError:
                    logger.error(
                        "provisioning_decrypt_failed",
                        device_id=str(device.id),
                        extension_id=str(extension.id),
                    )

        # Load device keys
        result = await session.execute(
            select(DeviceKey)
            .where(DeviceKey.device_id == device.id)
            .order_by(DeviceKey.key_section, DeviceKey.key_index)
        )
        keys = list(result.scalars().all())

        # Determine SIP server address
        sip_server = settings.freeswitch_host
        if sip_server in ("localhost", "0.0.0.0", "127.0.0.1"):
            sip_server = settings.provisioning_sip_server

        # Build config
        config_text, config_hash = build_config(
            device=device,
            extension=extension,
            tenant=tenant,
            phone_model=phone_model,
            keys=keys,
            sip_password=sip_password,
            sip_server=sip_server,
            ntp_server=settings.provisioning_ntp_server,
            timezone=settings.provisioning_timezone,
        )

        # Stamp provisioned
        await service.stamp_provisioned(device, config_hash)

        content_type = get_content_type(phone_model)

        logger.info(
            "provisioning_served",
            mac=mac,
            device_id=str(device.id),
            manufacturer=phone_model.manufacturer,
            extension=extension.extension_number if extension else None,
            config_hash=config_hash[:16],
        )

        return Response(
            content=config_text,
            media_type=f"{content_type}; charset=utf-8",
        )
