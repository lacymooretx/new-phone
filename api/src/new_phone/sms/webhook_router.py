"""SMS inbound + status webhooks — unauthenticated, called by providers.

Mounted outside /api/v1, similar to the provisioning endpoint.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Response, status

from new_phone.db.engine import AdminSessionLocal
from new_phone.services.sms_service import SMSService
from new_phone.sms.clearlyip import ClearlyIPProvider
from new_phone.sms.twilio import TwilioProvider

logger = structlog.get_logger()

router = APIRouter(tags=["sms-webhooks"])


@router.post("/sms/inbound/clearlyip")
async def clearlyip_inbound(request: Request) -> Response:
    """ClearlyIP inbound SMS webhook."""
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid JSON")

    provider = ClearlyIPProvider(trunk_token="")  # No token needed for parsing
    inbound = provider.parse_inbound_webhook(data)

    logger.info(
        "sms_inbound_clearlyip",
        from_number=inbound.from_number,
        to_number=inbound.to_number,
    )

    async with AdminSessionLocal() as session:
        service = SMSService(session)
        try:
            await service.receive_message(
                did_number=inbound.to_number,
                from_number=inbound.from_number,
                body=inbound.body,
                media_urls=inbound.media_urls or None,
                provider="clearlyip",
                provider_message_id=inbound.provider_message_id,
            )
        except ValueError as e:
            logger.warning("sms_inbound_clearlyip_rejected", error=str(e))
            if "not found" in str(e).lower():
                return Response(status_code=status.HTTP_404_NOT_FOUND, content=str(e))
            # Opted-out or other validation — still return 200 to prevent retries
            return Response(status_code=status.HTTP_200_OK)

    return Response(status_code=status.HTTP_200_OK)


@router.post("/sms/inbound/twilio")
async def twilio_inbound(request: Request) -> Response:
    """Twilio inbound SMS webhook."""
    try:
        body = await request.body()
        from urllib.parse import parse_qs
        raw = parse_qs(body.decode(), keep_blank_values=True)
        data = {k: v[0] if len(v) == 1 else v for k, v in raw.items()}
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid form data")

    provider = TwilioProvider(account_sid="", auth_token="")
    inbound = provider.parse_inbound_webhook(data)

    logger.info(
        "sms_inbound_twilio",
        from_number=inbound.from_number,
        to_number=inbound.to_number,
    )

    async with AdminSessionLocal() as session:
        service = SMSService(session)
        try:
            await service.receive_message(
                did_number=inbound.to_number,
                from_number=inbound.from_number,
                body=inbound.body,
                media_urls=inbound.media_urls or None,
                provider="twilio",
                provider_message_id=inbound.provider_message_id,
            )
        except ValueError as e:
            logger.warning("sms_inbound_twilio_rejected", error=str(e))
            if "not found" in str(e).lower():
                return Response(status_code=status.HTTP_404_NOT_FOUND, content=str(e))
            return Response(status_code=status.HTTP_200_OK)

    # Twilio expects TwiML or empty 200
    return Response(
        status_code=status.HTTP_200_OK,
        content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>",
        media_type="text/xml",
    )


@router.post("/sms/status/clearlyip")
async def clearlyip_status(request: Request) -> Response:
    """ClearlyIP delivery status callback."""
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid JSON")

    provider = ClearlyIPProvider(trunk_token="")
    update = provider.parse_status_callback(data)

    logger.debug(
        "sms_status_clearlyip",
        provider_message_id=update.provider_message_id,
        status=update.status,
    )

    async with AdminSessionLocal() as session:
        service = SMSService(session)
        await service.update_message_status(
            update.provider_message_id, update.status, update.error_message
        )

    return Response(status_code=status.HTTP_200_OK)


@router.post("/sms/status/twilio")
async def twilio_status(request: Request) -> Response:
    """Twilio delivery status callback."""
    try:
        body = await request.body()
        from urllib.parse import parse_qs
        raw = parse_qs(body.decode(), keep_blank_values=True)
        data = {k: v[0] if len(v) == 1 else v for k, v in raw.items()}
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid form data")

    provider = TwilioProvider(account_sid="", auth_token="")
    update = provider.parse_status_callback(data)

    logger.debug(
        "sms_status_twilio",
        provider_message_id=update.provider_message_id,
        status=update.status,
    )

    async with AdminSessionLocal() as session:
        service = SMSService(session)
        await service.update_message_status(
            update.provider_message_id, update.status, update.error_message
        )

    return Response(status_code=status.HTTP_200_OK)
