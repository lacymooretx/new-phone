"""Background periodic camp-on expiry task — runs every 60s to expire stale requests."""

import asyncio
import contextlib

import structlog

from new_phone.db.engine import AdminSessionLocal
from new_phone.services.camp_on_service import CampOnService

logger = structlog.get_logger()

CAMP_ON_INTERVAL_SECONDS = 60


class CampOnJob:
    def __init__(self, redis=None):
        self.redis = redis
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("camp_on_job_started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("camp_on_job_stopped")

    async def _loop(self) -> None:
        # Wait before first run so the app has time to fully start
        await asyncio.sleep(60)
        while True:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("camp_on_cycle_error")
            await asyncio.sleep(CAMP_ON_INTERVAL_SECONDS)

    async def _run_cycle(self) -> None:
        async with AdminSessionLocal() as db:
            service = CampOnService(db, redis=self.redis)
            expired_count = await service.expire_stale_requests()
        if expired_count:
            logger.info("camp_on_cycle_finished", expired=expired_count)
