import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.auth.passwords import hash_password
from new_phone.db.rls import set_tenant_context
from new_phone.models.voicemail_box import VoicemailBox
from new_phone.schemas.voicemail_box import VoicemailBoxCreate, VoicemailBoxUpdate


class VoicemailService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_voicemail_boxes(self, tenant_id: uuid.UUID) -> list[VoicemailBox]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(VoicemailBox)
            .where(VoicemailBox.tenant_id == tenant_id, VoicemailBox.is_active.is_(True))
            .order_by(VoicemailBox.mailbox_number)
        )
        return list(result.scalars().all())

    async def get_voicemail_box(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID
    ) -> VoicemailBox | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(VoicemailBox).where(
                VoicemailBox.id == box_id, VoicemailBox.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_voicemail_box(
        self, tenant_id: uuid.UUID, data: VoicemailBoxCreate
    ) -> VoicemailBox:
        await set_tenant_context(self.db, tenant_id)
        # Check for duplicate mailbox number in this tenant
        existing = await self.db.execute(
            select(VoicemailBox).where(
                VoicemailBox.tenant_id == tenant_id,
                VoicemailBox.mailbox_number == data.mailbox_number,
                VoicemailBox.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Mailbox number '{data.mailbox_number}' already exists")

        box = VoicemailBox(
            tenant_id=tenant_id,
            mailbox_number=data.mailbox_number,
            pin_hash=hash_password(data.pin),
            encrypted_pin=encrypt_value(data.pin),
            greeting_type=data.greeting_type,
            email_notification=data.email_notification,
            notification_email=data.notification_email,
            max_messages=data.max_messages,
        )
        self.db.add(box)
        await self.db.commit()
        await self.db.refresh(box)
        return box

    async def update_voicemail_box(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID, data: VoicemailBoxUpdate
    ) -> VoicemailBox:
        box = await self.get_voicemail_box(tenant_id, box_id)
        if not box:
            raise ValueError("Voicemail box not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(box, key, value)

        await self.db.commit()
        await self.db.refresh(box)
        return box

    async def deactivate_voicemail_box(
        self, tenant_id: uuid.UUID, box_id: uuid.UUID
    ) -> VoicemailBox:
        box = await self.get_voicemail_box(tenant_id, box_id)
        if not box:
            raise ValueError("Voicemail box not found")

        box.is_active = False
        box.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(box)
        return box

    async def reset_pin(self, tenant_id: uuid.UUID, box_id: uuid.UUID) -> str:
        box = await self.get_voicemail_box(tenant_id, box_id)
        if not box:
            raise ValueError("Voicemail box not found")

        new_pin = str(secrets.randbelow(9000) + 1000)  # 4-digit PIN
        box.pin_hash = hash_password(new_pin)
        box.encrypted_pin = encrypt_value(new_pin)
        await self.db.commit()
        return new_pin
