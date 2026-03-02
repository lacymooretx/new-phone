"""Recording storage tiering service — config CRUD, retrieval, legal hold, stats, tiering logic."""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.config import settings
from new_phone.db.rls import set_tenant_context
from new_phone.models.recording import Recording
from new_phone.models.recording_tier_config import RecordingTierConfig
from new_phone.schemas.recording_tier import (
    RecordingTierConfigCreate,
    RecordingTierConfigUpdate,
)
from new_phone.services.storage_service import StorageService

logger = structlog.get_logger()


class RecordingTierService:
    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.storage = storage

    # ── Config CRUD ──

    async def get_config(self, tenant_id: uuid.UUID) -> RecordingTierConfig | None:
        result = await self.db.execute(
            select(RecordingTierConfig).where(RecordingTierConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, tenant_id: uuid.UUID, data: RecordingTierConfigCreate
    ) -> RecordingTierConfig:
        existing = await self.get_config(tenant_id)
        if existing:
            raise ValueError("Tiering config already exists for this tenant")

        config = RecordingTierConfig(
            tenant_id=tenant_id,
            hot_tier_days=data.hot_tier_days,
            cold_tier_retention_days=data.cold_tier_retention_days,
            retrieval_cache_days=data.retrieval_cache_days,
            auto_tier_enabled=data.auto_tier_enabled,
            auto_delete_enabled=data.auto_delete_enabled,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(
        self, config_id: uuid.UUID, data: RecordingTierConfigUpdate
    ) -> RecordingTierConfig:
        result = await self.db.execute(
            select(RecordingTierConfig).where(RecordingTierConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Tiering config not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(RecordingTierConfig).where(RecordingTierConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Tiering config not found")
        await self.db.delete(config)
        await self.db.commit()

    # ── Retrieval ──

    async def request_retrieval(
        self, tenant_id: uuid.UUID, recording_id: uuid.UUID
    ) -> Recording | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Recording).where(
                Recording.id == recording_id,
                Recording.tenant_id == tenant_id,
                Recording.is_active.is_(True),
            )
        )
        recording = result.scalar_one_or_none()
        if not recording:
            return None

        if recording.storage_tier != "cold":
            return recording  # already hot

        # If already retrieved and not expired, return as-is
        if recording.retrieval_expires_at and recording.retrieval_expires_at > datetime.now(UTC):
            return recording

        # Copy from cold → hot
        if self.storage and recording.archive_storage_path:
            cold_bucket = recording.archive_storage_bucket or settings.minio_archive_bucket
            success = self.storage.copy_object(
                cold_bucket,
                recording.archive_storage_path,
                settings.minio_bucket,
                recording.archive_storage_path,
            )
            if not success:
                logger.error(
                    "retrieval_copy_failed",
                    recording_id=str(recording_id),
                    tenant_id=str(tenant_id),
                )
                return None

        # Get retrieval cache days from tenant config
        config = await self.get_config(tenant_id)
        cache_days = config.retrieval_cache_days if config else 7

        now = datetime.now(UTC)
        recording.retrieval_requested_at = now
        recording.retrieval_expires_at = now + timedelta(days=cache_days)
        recording.storage_path = recording.archive_storage_path
        recording.storage_bucket = settings.minio_bucket

        await self.db.commit()
        await self.db.refresh(recording)

        logger.info(
            "recording_retrieved",
            recording_id=str(recording_id),
            expires_at=recording.retrieval_expires_at.isoformat(),
        )
        return recording

    # ── Legal hold ──

    async def set_legal_hold(
        self,
        tenant_id: uuid.UUID,
        recording_ids: list[uuid.UUID],
        hold: bool,
        user_id: uuid.UUID | None = None,
    ) -> int:
        await set_tenant_context(self.db, tenant_id)
        now = datetime.now(UTC) if hold else None
        stmt = (
            update(Recording)
            .where(
                Recording.tenant_id == tenant_id,
                Recording.id.in_(recording_ids),
                Recording.is_active.is_(True),
            )
            .values(
                legal_hold=hold,
                legal_hold_set_by=user_id if hold else None,
                legal_hold_set_at=now,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(
            "legal_hold_updated",
            tenant_id=str(tenant_id),
            hold=hold,
            count=result.rowcount,
        )
        return result.rowcount

    # ── Storage stats ──

    async def get_storage_stats(self, tenant_id: uuid.UUID) -> dict:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(
                Recording.storage_tier,
                func.count(Recording.id).label("count"),
                func.coalesce(func.sum(Recording.file_size_bytes), 0).label("total_bytes"),
            )
            .where(
                Recording.tenant_id == tenant_id,
                Recording.is_active.is_(True),
            )
            .group_by(Recording.storage_tier)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        stats = {
            "hot_count": 0,
            "hot_bytes": 0,
            "cold_count": 0,
            "cold_bytes": 0,
            "legal_hold_count": 0,
            "total_bytes": 0,
        }
        for row in rows:
            tier = row.storage_tier
            if tier == "hot":
                stats["hot_count"] = row.count
                stats["hot_bytes"] = row.total_bytes
            elif tier == "cold":
                stats["cold_count"] = row.count
                stats["cold_bytes"] = row.total_bytes
            stats["total_bytes"] += row.total_bytes

        # Legal hold count (across tiers)
        hold_result = await self.db.execute(
            select(func.count(Recording.id)).where(
                Recording.tenant_id == tenant_id,
                Recording.is_active.is_(True),
                Recording.legal_hold.is_(True),
            )
        )
        stats["legal_hold_count"] = hold_result.scalar() or 0

        return stats

    # ── Tiering cycle ──

    async def run_tiering_cycle(self, tenant_id: uuid.UUID | None = None) -> dict:
        """Run one tiering cycle. If tenant_id is None, runs for all tenants with config."""
        if tenant_id:
            configs = []
            config = await self.get_config(tenant_id)
            if config and config.auto_tier_enabled and config.is_active:
                configs.append(config)
        else:
            result = await self.db.execute(
                select(RecordingTierConfig).where(
                    RecordingTierConfig.auto_tier_enabled.is_(True),
                    RecordingTierConfig.is_active.is_(True),
                )
            )
            configs = list(result.scalars().all())

        totals = {"archived": 0, "deleted": 0, "retrieval_expired": 0}

        for config in configs:
            try:
                result = await self._tier_tenant(config)
                totals["archived"] += result["archived"]
                totals["deleted"] += result["deleted"]
                totals["retrieval_expired"] += result["retrieval_expired"]
            except Exception:
                logger.exception("tiering_cycle_failed", tenant_id=str(config.tenant_id))

        return totals

    async def _tier_tenant(self, config: RecordingTierConfig) -> dict:
        now = datetime.now(UTC)
        tid = config.tenant_id
        await set_tenant_context(self.db, tid)

        result = {"archived": 0, "deleted": 0, "retrieval_expired": 0}

        # 1. Hot → Cold: recordings older than hot_tier_days
        hot_cutoff = now - timedelta(days=config.hot_tier_days)
        hot_recordings = await self.db.execute(
            select(Recording)
            .where(
                Recording.tenant_id == tid,
                Recording.storage_tier == "hot",
                Recording.is_active.is_(True),
                Recording.legal_hold.is_(False),
                Recording.created_at < hot_cutoff,
                Recording.retrieval_expires_at.is_(None),  # not a retrieved copy
            )
            .limit(500)
        )
        for rec in hot_recordings.scalars().all():
            if await self._move_to_cold(rec, config):
                result["archived"] += 1

        # 2. Cold → Delete: cold recordings past retention, if auto_delete_enabled
        if config.auto_delete_enabled:
            cold_cutoff = now - timedelta(days=config.cold_tier_retention_days)
            cold_recordings = await self.db.execute(
                select(Recording)
                .where(
                    Recording.tenant_id == tid,
                    Recording.storage_tier == "cold",
                    Recording.is_active.is_(True),
                    Recording.legal_hold.is_(False),
                    Recording.archived_at.isnot(None),
                    Recording.archived_at < cold_cutoff,
                )
                .limit(500)
            )
            for rec in cold_recordings.scalars().all():
                await self._permanent_delete(rec)
                result["deleted"] += 1

        # 3. Retrieval expiry: retrieved recordings past retrieval_expires_at
        expired_retrievals = await self.db.execute(
            select(Recording)
            .where(
                Recording.tenant_id == tid,
                Recording.storage_tier == "cold",
                Recording.is_active.is_(True),
                Recording.retrieval_expires_at.isnot(None),
                Recording.retrieval_expires_at < now,
            )
            .limit(500)
        )
        for rec in expired_retrievals.scalars().all():
            # Delete the hot copy, keep cold
            if self.storage and rec.storage_path:
                self.storage.delete_object(rec.storage_path)
            rec.storage_path = None
            rec.storage_bucket = None
            rec.retrieval_requested_at = None
            rec.retrieval_expires_at = None
            result["retrieval_expired"] += 1

        await self.db.commit()

        logger.info(
            "tiering_cycle_complete",
            tenant_id=str(tid),
            **result,
        )
        return result

    async def _move_to_cold(self, recording: Recording, config: RecordingTierConfig) -> bool:
        if not self.storage or not recording.storage_path:
            return False

        cold_bucket = settings.minio_archive_bucket
        archive_path = recording.storage_path

        success = self.storage.copy_object(
            settings.minio_bucket,
            recording.storage_path,
            cold_bucket,
            archive_path,
        )
        if not success:
            logger.error("archive_copy_failed", recording_id=str(recording.id))
            return False

        # Delete from hot bucket
        self.storage.delete_object(recording.storage_path)

        now = datetime.now(UTC)
        recording.storage_tier = "cold"
        recording.archived_at = now
        recording.archive_storage_path = archive_path
        recording.archive_storage_bucket = cold_bucket
        recording.storage_path = None
        recording.storage_bucket = None
        recording.retention_expires_at = now + timedelta(days=config.cold_tier_retention_days)

        return True

    async def _permanent_delete(self, recording: Recording) -> None:
        # Delete from cold bucket
        if self.storage and recording.archive_storage_path:
            cold_bucket = recording.archive_storage_bucket or settings.minio_archive_bucket
            self.storage.delete_object_from_bucket(cold_bucket, recording.archive_storage_path)
        # Also delete hot copy if it exists
        if self.storage and recording.storage_path:
            self.storage.delete_object(recording.storage_path)

        recording.is_active = False
        recording.storage_path = None
        recording.storage_bucket = None
        recording.archive_storage_path = None
        recording.archive_storage_bucket = None
