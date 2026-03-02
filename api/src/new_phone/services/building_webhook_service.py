import hashlib
import hmac
import secrets
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.building_webhook import (
    BuildingWebhook,
    BuildingWebhookAction,
    BuildingWebhookLog,
)
from new_phone.schemas.building_webhook import (
    BuildingWebhookActionCreate,
    BuildingWebhookCreate,
    BuildingWebhookUpdate,
)

logger = structlog.get_logger()


class BuildingWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_webhooks(self, tenant_id: uuid.UUID) -> list[BuildingWebhook]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BuildingWebhook)
            .where(BuildingWebhook.tenant_id == tenant_id, BuildingWebhook.is_active.is_(True))
            .options(selectinload(BuildingWebhook.actions))
            .order_by(BuildingWebhook.name)
        )
        return list(result.scalars().all())

    async def get_webhook(
        self, tenant_id: uuid.UUID, webhook_id: uuid.UUID
    ) -> BuildingWebhook | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BuildingWebhook)
            .where(BuildingWebhook.id == webhook_id, BuildingWebhook.tenant_id == tenant_id)
            .options(selectinload(BuildingWebhook.actions))
        )
        return result.scalar_one_or_none()

    async def create_webhook(
        self, tenant_id: uuid.UUID, data: BuildingWebhookCreate
    ) -> BuildingWebhook:
        await set_tenant_context(self.db, tenant_id)
        webhook = BuildingWebhook(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            secret_token=secrets.token_urlsafe(32),
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def update_webhook(
        self, tenant_id: uuid.UUID, webhook_id: uuid.UUID, data: BuildingWebhookUpdate
    ) -> BuildingWebhook:
        webhook = await self.get_webhook(tenant_id, webhook_id)
        if not webhook:
            raise ValueError("Building webhook not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(webhook, key, value)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def deactivate_webhook(
        self, tenant_id: uuid.UUID, webhook_id: uuid.UUID
    ) -> BuildingWebhook:
        webhook = await self.get_webhook(tenant_id, webhook_id)
        if not webhook:
            raise ValueError("Building webhook not found")
        webhook.is_active = False
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def add_action(
        self, tenant_id: uuid.UUID, webhook_id: uuid.UUID, data: BuildingWebhookActionCreate
    ) -> BuildingWebhookAction:
        await set_tenant_context(self.db, tenant_id)
        webhook = await self.get_webhook(tenant_id, webhook_id)
        if not webhook:
            raise ValueError("Building webhook not found")
        action = BuildingWebhookAction(
            tenant_id=tenant_id,
            webhook_id=webhook_id,
            **data.model_dump(),
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def remove_action(self, tenant_id: uuid.UUID, action_id: uuid.UUID) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BuildingWebhookAction).where(
                BuildingWebhookAction.id == action_id,
                BuildingWebhookAction.tenant_id == tenant_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise ValueError("Webhook action not found")
        await self.db.delete(action)
        await self.db.commit()

    async def list_logs(
        self, tenant_id: uuid.UUID, webhook_id: uuid.UUID, limit: int = 50
    ) -> list[BuildingWebhookLog]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BuildingWebhookLog)
            .where(
                BuildingWebhookLog.webhook_id == webhook_id,
                BuildingWebhookLog.tenant_id == tenant_id,
            )
            .order_by(BuildingWebhookLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def verify_signature(secret_token: str, payload_bytes: bytes, signature: str) -> bool:
        expected = hmac.new(secret_token.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def process_inbound(
        self, webhook: BuildingWebhook, source_ip: str, payload: dict, event_type: str | None
    ) -> BuildingWebhookLog:
        """Process an inbound building webhook event. Runs with AdminSession (no RLS)."""
        log_entry = BuildingWebhookLog(
            tenant_id=webhook.tenant_id,
            webhook_id=webhook.id,
            source_ip=source_ip,
            payload=payload,
            event_type=event_type,
            status="received",
        )
        self.db.add(log_entry)
        await self.db.flush()

        actions_taken = []
        try:
            # Match actions
            for action in sorted(webhook.actions, key=lambda a: a.priority):
                if not action.is_active:
                    continue
                if event_type and action.event_type_match == event_type:
                    action_result = {
                        "action_type": action.action_type,
                        "config": action.action_config,
                    }
                    if action.action_type == "panic_alert":
                        try:
                            from new_phone.models.panic_alert import TriggerSource
                            from new_phone.schemas.panic_alert import PanicAlertTriggerRequest
                            from new_phone.services.panic_alert_service import PanicAlertService

                            panic_service = PanicAlertService(self.db)
                            trigger_data = PanicAlertTriggerRequest(
                                alert_type=action.action_config.get("alert_type", "audible"),
                                trigger_source=TriggerSource.BUILDING_WEBHOOK,
                            )
                            await panic_service.trigger_alert(webhook.tenant_id, None, trigger_data)
                            action_result["status"] = "dispatched"
                        except Exception as e:
                            action_result["status"] = "failed"
                            action_result["error"] = str(e)
                    else:
                        logger.info(
                            "building_webhook_action",
                            action_type=action.action_type,
                            webhook_id=str(webhook.id),
                        )
                        action_result["status"] = "logged"
                    actions_taken.append(action_result)

            log_entry.actions_taken = actions_taken
            log_entry.status = "processed"
        except Exception as e:
            log_entry.status = "error"
            log_entry.error_message = str(e)
            logger.error("building_webhook_processing_error", error=str(e))

        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry
