import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.webhook import DeliveryStatus, WebhookDeliveryLog, WebhookSubscription

logger = structlog.get_logger()

MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 60  # seconds


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_subscriptions(self, tenant_id: uuid.UUID) -> list[WebhookSubscription]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
            .order_by(WebhookSubscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_subscription(self, tenant_id: uuid.UUID, subscription_id: uuid.UUID) -> WebhookSubscription | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_subscription(
        self, tenant_id: uuid.UUID, *, name: str, target_url: str, event_types: list[str],
        description: str | None = None, is_active: bool = True,
    ) -> WebhookSubscription:
        await set_tenant_context(self.db, tenant_id)
        import secrets
        secret = secrets.token_hex(32)
        sub = WebhookSubscription(
            tenant_id=tenant_id,
            name=name,
            target_url=target_url,
            secret=secret,
            event_types=event_types,
            description=description,
            is_active=is_active,
        )
        self.db.add(sub)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def update_subscription(
        self, tenant_id: uuid.UUID, subscription_id: uuid.UUID, **updates
    ) -> WebhookSubscription | None:
        sub = await self.get_subscription(tenant_id, subscription_id)
        if not sub:
            return None
        for key, val in updates.items():
            if val is not None and hasattr(sub, key):
                setattr(sub, key, val)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def delete_subscription(self, tenant_id: uuid.UUID, subscription_id: uuid.UUID) -> bool:
        sub = await self.get_subscription(tenant_id, subscription_id)
        if not sub:
            return False
        await self.db.delete(sub)
        await self.db.commit()
        return True

    async def list_delivery_logs(
        self, tenant_id: uuid.UUID, subscription_id: uuid.UUID, page: int = 1, per_page: int = 50,
    ) -> tuple[list[WebhookDeliveryLog], int]:
        await set_tenant_context(self.db, tenant_id)
        base = select(WebhookDeliveryLog).where(
            WebhookDeliveryLog.subscription_id == subscription_id,
            WebhookDeliveryLog.tenant_id == tenant_id,
        )
        total = (await self.db.execute(select(func.count(WebhookDeliveryLog.id)).where(
            WebhookDeliveryLog.subscription_id == subscription_id,
            WebhookDeliveryLog.tenant_id == tenant_id,
        ))).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            base.order_by(WebhookDeliveryLog.created_at.desc()).offset(offset).limit(per_page)
        )
        return list(result.scalars().all()), total

    async def test_webhook(self, tenant_id: uuid.UUID, subscription_id: uuid.UUID, event_type: str) -> WebhookDeliveryLog:
        sub = await self.get_subscription(tenant_id, subscription_id)
        if not sub:
            raise ValueError("Subscription not found")
        payload = {
            "event": event_type,
            "tenant_id": str(tenant_id),
            "payload": {"message": "This is a test webhook delivery"},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return await self._deliver(sub, event_type, payload)

    async def _deliver(self, sub: WebhookSubscription, event_type: str, payload: dict) -> WebhookDeliveryLog:
        body = json.dumps(payload, default=str)
        signature = hmac.new(sub.secret.encode(), body.encode(), hashlib.sha256).hexdigest()

        log = WebhookDeliveryLog(
            subscription_id=sub.id,
            tenant_id=sub.tenant_id,
            event_type=event_type,
            payload=payload,
            status=DeliveryStatus.PENDING,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    sub.target_url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={signature}",
                        "X-Webhook-Event": event_type,
                        "X-Webhook-Id": str(log.id),
                    },
                )
                log.response_status_code = resp.status_code
                log.response_body = resp.text[:4096] if resp.text else None
                if 200 <= resp.status_code < 300:
                    log.status = DeliveryStatus.SUCCESS
                    sub.failure_count = 0
                else:
                    log.status = DeliveryStatus.FAILED
                    log.error_message = f"HTTP {resp.status_code}"
                    sub.failure_count += 1
        except Exception as e:
            log.status = DeliveryStatus.FAILED
            log.error_message = str(e)[:1024]
            sub.failure_count += 1
            logger.warning("webhook_delivery_failed", subscription_id=str(sub.id), error=str(e))

        if log.status == DeliveryStatus.FAILED and log.attempt_count < MAX_RETRIES:
            log.status = DeliveryStatus.RETRYING
            backoff = RETRY_BACKOFF_BASE * (2 ** (log.attempt_count - 1))
            log.next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff)

        sub.last_triggered_at = datetime.now(UTC)
        self.db.add(log)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(log)
        return log


async def fan_out_webhooks(db: AsyncSession, tenant_id: uuid.UUID, event_type: str, payload: dict) -> None:
    """Called by EventPublisher to deliver events to matching webhook subscriptions."""
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.tenant_id == tenant_id,
            WebhookSubscription.is_active.is_(True),
        )
    )
    subscriptions = list(result.scalars().all())

    service = WebhookService(db)
    for sub in subscriptions:
        if event_type in sub.event_types or "*" in sub.event_types:
            envelope = {
                "event": event_type,
                "tenant_id": str(tenant_id),
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            try:
                await service._deliver(sub, event_type, envelope)
            except Exception as e:
                logger.error("webhook_fanout_error", subscription_id=str(sub.id), error=str(e))
