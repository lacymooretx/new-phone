"""Background periodic SMS retry task — retries failed messages with exponential backoff."""

import asyncio
import contextlib
import json
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.engine import AdminSessionLocal
from new_phone.models.sms import Message, MessageDirection, MessageStatus
from new_phone.sms.factory import get_tenant_default_provider

logger = structlog.get_logger()

SMS_RETRY_INTERVAL_SECONDS = 30
BACKOFF_SCHEDULE_SECONDS = [60, 300, 900]  # 1m, 5m, 15m


class SMSRetryJob:
    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("sms_retry_job_started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("sms_retry_job_stopped")

    async def _loop(self) -> None:
        # Wait before first run so the app has time to fully start
        await asyncio.sleep(30)
        while True:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("sms_retry_cycle_error")
            await asyncio.sleep(SMS_RETRY_INTERVAL_SECONDS)

    async def _run_cycle(self) -> None:
        async with AdminSessionLocal() as db:
            now = datetime.now(UTC)

            # Find messages eligible for retry
            result = await db.execute(
                select(Message)
                .where(
                    Message.status == MessageStatus.FAILED,
                    Message.direction == MessageDirection.OUTBOUND,
                    Message.retry_count < Message.max_retries,
                    Message.next_retry_at <= now,
                )
                .limit(50)  # Process in batches
            )
            messages = list(result.scalars().all())

            if not messages:
                return

            logger.info("sms_retry_cycle_found", count=len(messages))

            for message in messages:
                await self._retry_message(db, message)

    async def _retry_message(self, db: AsyncSession, message: Message) -> None:
        try:
            _config, provider = await get_tenant_default_provider(db, message.tenant_id)

            # Parse media URLs if present
            media_urls: list[str] | None = None
            if message.media_urls:
                try:
                    media_urls = json.loads(message.media_urls)
                except (json.JSONDecodeError, TypeError):
                    media_urls = None

            # Attempt re-send
            result = await provider.send_message(
                message.from_number,
                message.to_number,
                message.body,
                media_urls=media_urls,
            )

            if result.status in ("sent", "queued"):
                # Success — update message
                message.status = result.status
                message.provider_message_id = result.provider_message_id
                message.segments = result.segments
                message.error_message = None
                message.retry_count = message.retry_count + 1
                message.next_retry_at = None
                await db.commit()
                logger.info(
                    "sms_retry_success",
                    message_id=str(message.id),
                    retry_count=message.retry_count,
                )
            else:
                # Still failed — schedule next retry or mark permanently failed
                await self._schedule_next_retry(db, message)

        except Exception as e:
            logger.error(
                "sms_retry_error",
                message_id=str(message.id),
                error=str(e),
            )
            await self._schedule_next_retry(db, message)

    async def _schedule_next_retry(self, db: AsyncSession, message: Message) -> None:
        message.retry_count = message.retry_count + 1
        now = datetime.now(UTC)

        if message.retry_count >= message.max_retries:
            # Max retries reached — mark permanently failed
            message.status = "permanently_failed"
            message.next_retry_at = None
            logger.warning(
                "sms_retry_permanently_failed",
                message_id=str(message.id),
                retry_count=message.retry_count,
            )
        else:
            # Exponential backoff
            backoff_index = min(message.retry_count - 1, len(BACKOFF_SCHEDULE_SECONDS) - 1)
            delay_seconds = BACKOFF_SCHEDULE_SECONDS[backoff_index]
            message.next_retry_at = now + timedelta(seconds=delay_seconds)
            logger.info(
                "sms_retry_scheduled",
                message_id=str(message.id),
                retry_count=message.retry_count,
                next_retry_at=message.next_retry_at.isoformat(),
            )

        await db.commit()
