import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.voicemail_box import VoicemailBox
from new_phone.models.voicemail_message import VoicemailMessage
from new_phone.schemas.voicemail_message import VoicemailMessageFilter, VoicemailMessageUpdate
from new_phone.services.storage_service import StorageService


class VoicemailMessageService:
    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.storage = storage

    async def list_messages(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, filters: VoicemailMessageFilter
    ) -> list[VoicemailMessage]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(VoicemailMessage).where(
            VoicemailMessage.tenant_id == tenant_id,
            VoicemailMessage.voicemail_box_id == box_id,
            VoicemailMessage.is_active.is_(True),
        )
        if filters.folder:
            stmt = stmt.where(VoicemailMessage.folder == filters.folder)
        if filters.is_read is not None:
            stmt = stmt.where(VoicemailMessage.is_read == filters.is_read)
        if filters.date_from:
            stmt = stmt.where(VoicemailMessage.created_at >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(VoicemailMessage.created_at <= filters.date_to)
        stmt = stmt.order_by(VoicemailMessage.created_at.desc())
        stmt = stmt.offset(filters.offset).limit(filters.limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_message(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, message_id: uuid.UUID
    ) -> VoicemailMessage | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(VoicemailMessage).where(
                VoicemailMessage.id == message_id,
                VoicemailMessage.tenant_id == tenant_id,
                VoicemailMessage.voicemail_box_id == box_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_playback_url(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, message_id: uuid.UUID
    ) -> str | None:
        msg = await self.get_message(tenant_id, box_id, message_id)
        if not msg or not msg.storage_path or not self.storage:
            return None
        return self.storage.presigned_url(msg.storage_path)

    async def update_message(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, message_id: uuid.UUID, data: VoicemailMessageUpdate
    ) -> VoicemailMessage | None:
        msg = await self.get_message(tenant_id, box_id, message_id)
        if not msg:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(msg, key, value)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def soft_delete(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, message_id: uuid.UUID
    ) -> VoicemailMessage | None:
        msg = await self.get_message(tenant_id, box_id, message_id)
        if not msg:
            return None
        msg.is_active = False
        msg.folder = "deleted"
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def forward_message(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, message_id: uuid.UUID, target_box_id: uuid.UUID
    ) -> VoicemailMessage | None:
        msg = await self.get_message(tenant_id, box_id, message_id)
        if not msg:
            return None

        # Verify target box exists in same tenant
        result = await self.db.execute(
            select(VoicemailBox).where(
                VoicemailBox.id == target_box_id,
                VoicemailBox.tenant_id == tenant_id,
                VoicemailBox.is_active.is_(True),
            )
        )
        target_box = result.scalar_one_or_none()
        if not target_box:
            raise ValueError("Target voicemail box not found")

        # Create a copy of the message in the target box
        new_msg = VoicemailMessage(
            tenant_id=tenant_id,
            voicemail_box_id=target_box_id,
            caller_number=msg.caller_number,
            caller_name=msg.caller_name,
            duration_seconds=msg.duration_seconds,
            storage_path=msg.storage_path,
            storage_bucket=msg.storage_bucket,
            file_size_bytes=msg.file_size_bytes,
            format=msg.format,
            sha256_hash=msg.sha256_hash,
            call_id=msg.call_id,
        )
        self.db.add(new_msg)
        await self.db.commit()
        await self.db.refresh(new_msg)
        return new_msg

    async def get_unread_counts(
        self, tenant_id: uuid.UUID
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(
                VoicemailMessage.voicemail_box_id,
                VoicemailBox.mailbox_number,
                func.count(VoicemailMessage.id).label("unread_count"),
            )
            .join(VoicemailBox, VoicemailMessage.voicemail_box_id == VoicemailBox.id)
            .where(
                VoicemailMessage.tenant_id == tenant_id,
                VoicemailMessage.is_active.is_(True),
                VoicemailMessage.is_read.is_(False),
                VoicemailMessage.folder == "new",
            )
            .group_by(VoicemailMessage.voicemail_box_id, VoicemailBox.mailbox_number)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "voicemail_box_id": row.voicemail_box_id,
                "mailbox_number": row.mailbox_number,
                "unread_count": row.unread_count,
            }
            for row in result.all()
        ]

    async def cleanup_old_messages(self, cutoff: datetime) -> int:
        """Permanently delete messages older than cutoff. Used by admin cleanup."""
        stmt = select(VoicemailMessage).where(
            VoicemailMessage.created_at < cutoff,
            VoicemailMessage.folder == "deleted",
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        count = len(messages)
        for msg in messages:
            await self.db.delete(msg)
        if count > 0:
            await self.db.commit()
        return count
