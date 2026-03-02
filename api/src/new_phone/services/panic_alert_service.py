import asyncio
import uuid
from datetime import UTC, datetime
from typing import ClassVar

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.panic_alert import AlertStatus, PanicAlert
from new_phone.models.security_config import SecurityConfig
from new_phone.schemas.panic_alert import PanicAlertResolveRequest, PanicAlertTriggerRequest

logger = structlog.get_logger()


class PanicAlertService:
    _background_tasks: ClassVar[set[asyncio.Task]] = set()

    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_alert(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID | None, data: PanicAlertTriggerRequest
    ) -> PanicAlert:
        await set_tenant_context(self.db, tenant_id)
        alert = PanicAlert(
            tenant_id=tenant_id,
            triggered_by_user_id=user_id,
            triggered_from_extension_id=data.extension_id,
            trigger_source=data.trigger_source,
            alert_type=data.alert_type,
            status=AlertStatus.ACTIVE,
            location_building=data.location_building,
            location_floor=data.location_floor,
            location_description=data.location_description,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        logger.critical(
            "panic_alert_triggered",
            alert_id=str(alert.id),
            tenant_id=str(tenant_id),
            trigger_source=data.trigger_source,
            alert_type=data.alert_type,
        )

        # Fire-and-forget notification dispatch
        task = asyncio.create_task(self._dispatch_notifications(tenant_id, alert.id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return alert

    async def get_alert(self, tenant_id: uuid.UUID, alert_id: uuid.UUID) -> PanicAlert | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PanicAlert).where(PanicAlert.id == alert_id, PanicAlert.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self, tenant_id: uuid.UUID, status_filter: str | None = None, limit: int = 50
    ) -> list[PanicAlert]:
        await set_tenant_context(self.db, tenant_id)
        query = select(PanicAlert).where(PanicAlert.tenant_id == tenant_id)
        if status_filter:
            query = query.where(PanicAlert.status == status_filter)
        query = query.order_by(PanicAlert.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge(
        self, tenant_id: uuid.UUID, alert_id: uuid.UUID, user_id: uuid.UUID
    ) -> PanicAlert:
        await set_tenant_context(self.db, tenant_id)
        alert = await self.get_alert(tenant_id, alert_id)
        if not alert:
            raise ValueError("Panic alert not found")
        if alert.status != AlertStatus.ACTIVE:
            raise ValueError(f"Alert is not active (current status: {alert.status})")
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by_user_id = user_id
        alert.acknowledged_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info("panic_alert_acknowledged", alert_id=str(alert_id), user_id=str(user_id))

        # Publish event
        task = asyncio.create_task(
            self._publish_event(tenant_id, "panic.alert_acknowledged", {"alert_id": str(alert_id)})
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return alert

    async def resolve(
        self,
        tenant_id: uuid.UUID,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PanicAlertResolveRequest,
    ) -> PanicAlert:
        await set_tenant_context(self.db, tenant_id)
        alert = await self.get_alert(tenant_id, alert_id)
        if not alert:
            raise ValueError("Panic alert not found")
        if alert.status == AlertStatus.RESOLVED or alert.status == AlertStatus.FALSE_ALARM:
            raise ValueError(f"Alert already resolved (status: {alert.status})")
        alert.status = AlertStatus.FALSE_ALARM if data.mark_false_alarm else AlertStatus.RESOLVED
        alert.resolved_by_user_id = user_id
        alert.resolved_at = datetime.now(UTC)
        alert.resolution_notes = data.resolution_notes
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info("panic_alert_resolved", alert_id=str(alert_id), status=alert.status)
        task = asyncio.create_task(
            self._publish_event(
                tenant_id,
                "panic.alert_resolved",
                {"alert_id": str(alert_id), "status": alert.status},
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return alert

    async def _dispatch_notifications(self, tenant_id: uuid.UUID, alert_id: uuid.UUID) -> None:
        """Fire-and-forget: dispatch notifications for a panic alert."""
        try:
            from new_phone.db.engine import AdminSessionLocal

            async with AdminSessionLocal() as session:
                config_result = await session.execute(
                    select(SecurityConfig).where(SecurityConfig.tenant_id == tenant_id)
                )
                config = config_result.scalar_one_or_none()
                if not config or not config.notification_targets:
                    return

                alert_result = await session.execute(
                    select(PanicAlert).where(PanicAlert.id == alert_id)
                )
                alert = alert_result.scalar_one_or_none()
                if not alert:
                    return

                for target in sorted(config.notification_targets, key=lambda t: t.priority):
                    if not target.is_active:
                        continue
                    try:
                        if target.target_type == "webhook":
                            import httpx

                            async with httpx.AsyncClient(timeout=10) as client:
                                await client.post(
                                    target.target_value,
                                    json={
                                        "event": "panic_alert",
                                        "alert_id": str(alert.id),
                                        "tenant_id": str(tenant_id),
                                        "alert_type": alert.alert_type,
                                        "trigger_source": alert.trigger_source,
                                        "status": alert.status,
                                        "created_at": alert.created_at.isoformat(),
                                    },
                                )
                        else:
                            logger.info(
                                "panic_notification_dispatched",
                                target_type=target.target_type,
                                target_value=target.target_value,
                                alert_id=str(alert_id),
                            )
                    except Exception as e:
                        logger.error(
                            "panic_notification_failed",
                            target_type=target.target_type,
                            error=str(e),
                        )

        except Exception as e:
            logger.error("panic_dispatch_error", alert_id=str(alert_id), error=str(e))

    async def _publish_event(self, tenant_id: uuid.UUID, event_type: str, data: dict) -> None:
        """Publish a panic event via Redis EventPublisher."""
        try:
            from new_phone.main import event_publisher

            if event_publisher:
                await event_publisher.publish(tenant_id, event_type, data)
        except Exception as e:
            logger.error("panic_event_publish_failed", event_type=event_type, error=str(e))
