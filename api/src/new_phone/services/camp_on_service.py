"""Camp-On / Automatic Callback service — config CRUD, request management, Redis sync."""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.camp_on import CampOnConfig, CampOnRequest, CampOnStatus
from new_phone.models.extension import Extension
from new_phone.schemas.camp_on import (
    CampOnConfigCreate,
    CampOnConfigUpdate,
    CampOnCreateRequest,
)

logger = structlog.get_logger()


class CampOnService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    # ── Config CRUD ──

    async def get_config(self, tenant_id: uuid.UUID) -> CampOnConfig | None:
        result = await self.db.execute(
            select(CampOnConfig).where(CampOnConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_config(self, tenant_id: uuid.UUID, data: CampOnConfigCreate) -> CampOnConfig:
        existing = await self.get_config(tenant_id)
        if existing:
            raise ValueError("Camp-on config already exists for this tenant")

        config = CampOnConfig(
            tenant_id=tenant_id,
            enabled=data.enabled,
            feature_code=data.feature_code,
            timeout_minutes=data.timeout_minutes,
            max_camp_ons_per_target=data.max_camp_ons_per_target,
            callback_retry_delay_seconds=data.callback_retry_delay_seconds,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(self, config_id: uuid.UUID, data: CampOnConfigUpdate) -> CampOnConfig:
        result = await self.db.execute(select(CampOnConfig).where(CampOnConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Camp-on config not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(select(CampOnConfig).where(CampOnConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Camp-on config not found")
        await self.db.delete(config)
        await self.db.commit()

    # ── Request management ──

    async def create_request(
        self, tenant_id: uuid.UUID, data: CampOnCreateRequest
    ) -> CampOnRequest:
        # Load config
        config = await self.get_config(tenant_id)
        if not config or not config.enabled or not config.is_active:
            raise ValueError("Camp-on is not enabled for this tenant")

        # Resolve caller extension
        caller_ext = await self._resolve_extension(tenant_id, data.caller_extension_number)
        if not caller_ext:
            raise ValueError(f"Caller extension {data.caller_extension_number} not found")

        # Resolve target extension
        target_ext = await self._resolve_extension(tenant_id, data.target_extension_number)
        if not target_ext:
            raise ValueError(f"Target extension {data.target_extension_number} not found")

        # Same extension check
        if caller_ext.id == target_ext.id:
            raise ValueError("Cannot camp on your own extension")

        # Check max camp-ons per target
        pending_count_result = await self.db.execute(
            select(CampOnRequest).where(
                CampOnRequest.tenant_id == tenant_id,
                CampOnRequest.target_extension_id == target_ext.id,
                CampOnRequest.status == CampOnStatus.pending.value,
            )
        )
        pending = list(pending_count_result.scalars().all())
        if len(pending) >= config.max_camp_ons_per_target:
            raise ValueError("Maximum camp-on requests for this target reached")

        # Check for duplicate (same caller already pending for same target)
        for req in pending:
            if req.caller_extension_id == caller_ext.id:
                raise ValueError("You already have a pending camp-on for this target")

        expires_at = datetime.now(UTC) + timedelta(minutes=config.timeout_minutes)

        request = CampOnRequest(
            tenant_id=tenant_id,
            caller_extension_id=caller_ext.id,
            target_extension_id=target_ext.id,
            caller_extension_number=data.caller_extension_number,
            target_extension_number=data.target_extension_number,
            caller_sip_username=caller_ext.sip_username,
            target_sip_username=target_ext.sip_username,
            reason=data.reason,
            original_call_id=data.original_call_id,
            expires_at=expires_at,
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)

        # Add to Redis for fast lookup
        await self._add_to_redis(tenant_id, data.target_extension_number, request.id)

        # Publish WebSocket event
        await self._publish_event(
            tenant_id,
            "campon.created",
            {
                "request_id": str(request.id),
                "caller_extension_number": data.caller_extension_number,
                "target_extension_number": data.target_extension_number,
                "reason": data.reason,
                "expires_at": expires_at.isoformat(),
            },
        )

        logger.info(
            "camp_on_created",
            request_id=str(request.id),
            caller=data.caller_extension_number,
            target=data.target_extension_number,
            reason=data.reason,
        )
        return request

    async def list_requests(
        self,
        tenant_id: uuid.UUID,
        status_filter: str | None = None,
        target_ext: str | None = None,
    ) -> list[CampOnRequest]:
        stmt = select(CampOnRequest).where(CampOnRequest.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(CampOnRequest.status == status_filter)
        if target_ext:
            stmt = stmt.where(CampOnRequest.target_extension_number == target_ext)
        stmt = stmt.order_by(CampOnRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_request(
        self, tenant_id: uuid.UUID, request_id: uuid.UUID
    ) -> CampOnRequest | None:
        result = await self.db.execute(
            select(CampOnRequest).where(
                CampOnRequest.id == request_id,
                CampOnRequest.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def cancel_request(self, tenant_id: uuid.UUID, request_id: uuid.UUID) -> CampOnRequest:
        request = await self.get_request(tenant_id, request_id)
        if not request:
            raise ValueError("Camp-on request not found")
        if request.status != CampOnStatus.pending.value:
            raise ValueError(f"Cannot cancel request in {request.status} status")

        request.status = CampOnStatus.cancelled.value
        request.cancelled_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(request)

        await self._remove_from_redis(tenant_id, request.target_extension_number, request.id)

        await self._publish_event(
            tenant_id,
            "campon.cancelled",
            {
                "request_id": str(request.id),
                "caller_extension_number": request.caller_extension_number,
                "target_extension_number": request.target_extension_number,
            },
        )

        logger.info("camp_on_cancelled", request_id=str(request_id))
        return request

    async def initiate_callback(self, request_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(CampOnRequest).where(CampOnRequest.id == request_id))
        request = result.scalar_one_or_none()
        if not request or request.status != CampOnStatus.pending.value:
            return False

        request.status = CampOnStatus.callback_initiated.value
        request.callback_initiated_at = datetime.now(UTC)
        request.callback_attempts += 1
        await self.db.commit()

        logger.info(
            "camp_on_callback_initiated",
            request_id=str(request_id),
            attempt=request.callback_attempts,
        )
        return True

    async def handle_callback_success(self, request_id: uuid.UUID) -> None:
        result = await self.db.execute(select(CampOnRequest).where(CampOnRequest.id == request_id))
        request = result.scalar_one_or_none()
        if not request:
            return

        request.status = CampOnStatus.connected.value
        request.connected_at = datetime.now(UTC)
        await self.db.commit()

        await self._remove_from_redis(
            request.tenant_id, request.target_extension_number, request.id
        )

        await self._publish_event(
            request.tenant_id,
            "campon.connected",
            {
                "request_id": str(request.id),
                "caller_extension_number": request.caller_extension_number,
                "target_extension_number": request.target_extension_number,
            },
        )

        logger.info("camp_on_connected", request_id=str(request_id))

    async def handle_callback_failure(self, request_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(CampOnRequest).where(CampOnRequest.id == request_id))
        request = result.scalar_one_or_none()
        if not request:
            return False

        if request.callback_attempts < 2:
            # Reset to pending for retry
            request.status = CampOnStatus.pending.value
            await self.db.commit()
            logger.info(
                "camp_on_callback_retry_scheduled",
                request_id=str(request_id),
                attempt=request.callback_attempts,
            )
            return True  # Caller: should retry after delay
        else:
            # Max attempts reached
            request.status = CampOnStatus.caller_unavailable.value
            await self.db.commit()

            await self._remove_from_redis(
                request.tenant_id, request.target_extension_number, request.id
            )

            await self._publish_event(
                request.tenant_id,
                "campon.failed",
                {
                    "request_id": str(request.id),
                    "caller_extension_number": request.caller_extension_number,
                    "target_extension_number": request.target_extension_number,
                    "reason": "caller_unavailable",
                },
            )

            logger.info("camp_on_caller_unavailable", request_id=str(request_id))
            return False  # No more retries

    async def expire_stale_requests(self) -> int:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(CampOnRequest).where(
                CampOnRequest.status == CampOnStatus.pending.value,
                CampOnRequest.expires_at < now,
            )
        )
        expired = list(result.scalars().all())

        for req in expired:
            req.status = CampOnStatus.expired.value
            await self._remove_from_redis(req.tenant_id, req.target_extension_number, req.id)
            await self._publish_event(
                req.tenant_id,
                "campon.expired",
                {
                    "request_id": str(req.id),
                    "caller_extension_number": req.caller_extension_number,
                    "target_extension_number": req.target_extension_number,
                },
            )

        if expired:
            await self.db.commit()
            logger.info("camp_on_expired", count=len(expired))

        return len(expired)

    # ── Redis helpers ──

    async def _add_to_redis(
        self, tenant_id: uuid.UUID, target_ext_number: str, request_id: uuid.UUID
    ) -> None:
        if not self.redis:
            return
        try:
            key = f"campon:{tenant_id}:{target_ext_number}"
            await self.redis.sadd(key, str(request_id))
            # TTL = max config timeout + buffer
            await self.redis.expire(key, 86400)
        except Exception as e:
            logger.warning("camp_on_redis_add_error", error=str(e))

    async def _remove_from_redis(
        self, tenant_id: uuid.UUID, target_ext_number: str, request_id: uuid.UUID
    ) -> None:
        if not self.redis:
            return
        try:
            key = f"campon:{tenant_id}:{target_ext_number}"
            await self.redis.srem(key, str(request_id))
            # Clean up empty sets
            remaining = await self.redis.scard(key)
            if remaining == 0:
                await self.redis.delete(key)
        except Exception as e:
            logger.warning("camp_on_redis_remove_error", error=str(e))

    async def get_pending_for_target(
        self, tenant_id: uuid.UUID, target_ext_number: str
    ) -> list[str]:
        if not self.redis:
            return []
        try:
            key = f"campon:{tenant_id}:{target_ext_number}"
            members = await self.redis.smembers(key)
            return list(members)
        except Exception as e:
            logger.warning("camp_on_redis_get_error", error=str(e))
            return []

    # ── Internal helpers ──

    async def _resolve_extension(self, tenant_id: uuid.UUID, ext_number: str) -> Extension | None:
        result = await self.db.execute(
            select(Extension).where(
                Extension.tenant_id == tenant_id,
                Extension.extension_number == ext_number,
                Extension.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _publish_event(self, tenant_id: uuid.UUID, event_type: str, payload: dict) -> None:
        try:
            from new_phone.main import event_publisher

            if event_publisher:
                await event_publisher.publish(tenant_id, event_type, payload)
        except Exception as e:
            logger.warning("camp_on_event_publish_error", error=str(e))
