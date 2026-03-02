"""Building system inbound webhooks — unauthenticated, HMAC-validated.

Mounted outside /api/v1, similar to SMS webhooks.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from new_phone.db.engine import AdminSessionLocal
from new_phone.models.building_webhook import BuildingWebhook
from new_phone.services.building_webhook_service import BuildingWebhookService

logger = structlog.get_logger()

router = APIRouter(tags=["building-webhooks"])


@router.post("/webhooks/building/{webhook_id}")
async def building_webhook_inbound(webhook_id: uuid.UUID, request: Request) -> Response:
    """Receive inbound webhook from building alarm/access system."""
    # Read raw body for HMAC verification
    body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid JSON")

    # Extract signature from header
    signature = request.headers.get("X-Webhook-Signature", "")

    # Get source IP
    source_ip = request.client.host if request.client else "unknown"

    async with AdminSessionLocal() as session:
        # Load webhook with actions
        result = await session.execute(
            select(BuildingWebhook)
            .where(BuildingWebhook.id == webhook_id, BuildingWebhook.is_active.is_(True))
            .options(selectinload(BuildingWebhook.actions))
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            logger.warning("building_webhook_not_found", webhook_id=str(webhook_id))
            return Response(status_code=status.HTTP_404_NOT_FOUND, content="Webhook not found")

        # Verify HMAC signature
        if signature:
            if not BuildingWebhookService.verify_signature(webhook.secret_token, body, signature):
                logger.warning("building_webhook_invalid_signature", webhook_id=str(webhook_id))
                return Response(
                    status_code=status.HTTP_401_UNAUTHORIZED, content="Invalid signature"
                )
        else:
            logger.warning("building_webhook_no_signature", webhook_id=str(webhook_id))
            return Response(
                status_code=status.HTTP_401_UNAUTHORIZED, content="Missing signature"
            )

        # Extract event type from payload
        event_type = payload.get("event_type") or payload.get("type") or payload.get("event")

        logger.info(
            "building_webhook_received",
            webhook_id=str(webhook_id),
            event_type=event_type,
            source_ip=source_ip,
        )

        # Process the webhook
        service = BuildingWebhookService(session)
        await service.process_inbound(webhook, source_ip, payload, event_type)

    return Response(status_code=status.HTTP_200_OK)
