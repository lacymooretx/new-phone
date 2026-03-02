"""SMS inbound + status webhooks — unauthenticated, called by providers.

Mounted outside /api/v1, similar to the provisioning endpoint.
"""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from new_phone.auth.encryption import decrypt_value
from new_phone.db.engine import AdminSessionLocal
from new_phone.models.did import DID
from new_phone.models.sms import SMSProvider, SMSProviderConfig
from new_phone.services.sms_service import SMSService
from new_phone.sms.clearlyip import ClearlyIPProvider
from new_phone.sms.twilio import TwilioProvider

logger = structlog.get_logger()

router = APIRouter(tags=["sms-webhooks"])


async def _get_provider_config_for_did(
    session, did_number: str, provider_type: str
) -> SMSProviderConfig | None:
    """Look up the active SMS provider config for a DID's tenant."""
    result = await session.execute(
        select(DID).where(DID.number == did_number, DID.sms_enabled.is_(True))
    )
    did = result.scalar_one_or_none()
    if not did:
        return None

    result = await session.execute(
        select(SMSProviderConfig).where(
            SMSProviderConfig.tenant_id == did.tenant_id,
            SMSProviderConfig.provider_type == provider_type,
            SMSProviderConfig.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


@router.post("/sms/inbound/clearlyip")
async def clearlyip_inbound(request: Request) -> Response:
    """ClearlyIP inbound SMS webhook."""
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid JSON")

    provider = ClearlyIPProvider(trunk_token="")  # No token needed for parsing

    # ClearlyIP doesn't provide HMAC — verify returns True (validates via known DID matching)
    if not await provider.verify_webhook_signature(request):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, content="Invalid signature")

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

    # Parse to get the DID number, then verify signature with real auth_token
    temp_provider = TwilioProvider(account_sid="", auth_token="")
    inbound = temp_provider.parse_inbound_webhook(data)

    async with AdminSessionLocal() as session:
        # Look up the Twilio provider config to get the real auth_token for signature verification
        config = await _get_provider_config_for_did(session, inbound.to_number, SMSProvider.TWILIO)
        if config:
            try:
                creds = json.loads(decrypt_value(config.encrypted_credentials))
                verified_provider = TwilioProvider(
                    account_sid=creds.get("account_sid", ""),
                    auth_token=creds.get("auth_token", ""),
                )
                if not await verified_provider.verify_webhook_signature(request):
                    logger.warning("twilio_webhook_signature_invalid", to_number=inbound.to_number)
                    return Response(status_code=status.HTTP_401_UNAUTHORIZED, content="Invalid signature")
            except (ValueError, json.JSONDecodeError):
                logger.warning("twilio_webhook_credential_decrypt_failed", to_number=inbound.to_number)
        else:
            logger.warning("twilio_webhook_no_provider_config", to_number=inbound.to_number)

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

    # ClearlyIP doesn't provide HMAC — verify returns True (validates via known DID matching)
    if not await provider.verify_webhook_signature(request):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, content="Invalid signature")

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

    # Verify Twilio signature — look up From number (the DID) from status callback
    to_number = data.get("To", data.get("From", ""))
    if to_number:
        async with AdminSessionLocal() as sig_session:
            config = await _get_provider_config_for_did(sig_session, to_number, SMSProvider.TWILIO)
            if config:
                try:
                    creds = json.loads(decrypt_value(config.encrypted_credentials))
                    verified_provider = TwilioProvider(
                        account_sid=creds.get("account_sid", ""),
                        auth_token=creds.get("auth_token", ""),
                    )
                    if not await verified_provider.verify_webhook_signature(request):
                        logger.warning("twilio_status_webhook_signature_invalid")
                        return Response(status_code=status.HTTP_401_UNAUTHORIZED, content="Invalid signature")
                except (ValueError, json.JSONDecodeError):
                    logger.warning("twilio_status_webhook_credential_decrypt_failed")

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
