import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.recording import Recording
from new_phone.schemas.recording import RecordingFilter
from new_phone.services.storage_service import StorageService


class RecordingService:
    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.storage = storage

    async def list_recordings(
        self, tenant_id: uuid.UUID, filters: RecordingFilter
    ) -> list[Recording]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(Recording).where(
            Recording.tenant_id == tenant_id,
            Recording.is_active.is_(True),
        )

        if filters.date_from:
            stmt = stmt.where(Recording.created_at >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Recording.created_at <= filters.date_to)
        if filters.call_id:
            stmt = stmt.where(Recording.call_id == filters.call_id)
        if filters.cdr_id:
            stmt = stmt.where(Recording.cdr_id == filters.cdr_id)
        if filters.storage_tier:
            stmt = stmt.where(Recording.storage_tier == filters.storage_tier)
        if filters.legal_hold is not None:
            stmt = stmt.where(Recording.legal_hold.is_(filters.legal_hold))

        stmt = stmt.order_by(Recording.created_at.desc())
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recording(
        self, tenant_id: uuid.UUID, recording_id: uuid.UUID
    ) -> Recording | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Recording).where(
                Recording.id == recording_id,
                Recording.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_playback_url(self, tenant_id: uuid.UUID, recording_id: uuid.UUID) -> dict:
        """Returns {"url": str, "status": "available"} or {"url": None, "status": "cold|missing"}."""
        recording = await self.get_recording(tenant_id, recording_id)
        if not recording or not self.storage:
            return {"url": None, "status": "missing"}

        # Cold recording without active retrieval
        if recording.storage_tier == "cold" and not recording.storage_path:
            return {"url": None, "status": "cold"}

        if not recording.storage_path:
            return {"url": None, "status": "missing"}

        url = self.storage.presigned_url(recording.storage_path)
        return {"url": url, "status": "available"}

    async def soft_delete(self, tenant_id: uuid.UUID, recording_id: uuid.UUID) -> Recording | None:
        recording = await self.get_recording(tenant_id, recording_id)
        if not recording:
            return None
        recording.is_active = False
        await self.db.commit()
        await self.db.refresh(recording)
        return recording
