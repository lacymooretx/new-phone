"""Background periodic tiering task — runs daily to move recordings between tiers."""

import asyncio
import contextlib

import structlog

from new_phone.db.engine import AdminSessionLocal
from new_phone.services.recording_tier_service import RecordingTierService
from new_phone.services.storage_service import StorageService

logger = structlog.get_logger()

TIERING_INTERVAL_SECONDS = 86400  # 24 hours


class TieringJob:
    def __init__(self, storage: StorageService | None = None):
        self.storage = storage
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("tiering_job_started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("tiering_job_stopped")

    async def _loop(self) -> None:
        # Wait before first run so the app has time to fully start
        await asyncio.sleep(60)
        while True:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("tiering_cycle_error")
            await asyncio.sleep(TIERING_INTERVAL_SECONDS)

    async def _run_cycle(self) -> None:
        logger.info("tiering_cycle_starting")
        async with AdminSessionLocal() as db:
            service = RecordingTierService(db, storage=self.storage)
            totals = await service.run_tiering_cycle()
        logger.info("tiering_cycle_finished", **totals)
