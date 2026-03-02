import hashlib
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.audio_prompt import AudioPrompt
from new_phone.services.storage_service import StorageService


class AudioPromptService:
    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.storage = storage

    async def list_prompts(
        self, tenant_id: uuid.UUID, category: str | None = None, site_id: uuid.UUID | None = None
    ) -> list[AudioPrompt]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(AudioPrompt).where(
            AudioPrompt.tenant_id == tenant_id,
            AudioPrompt.is_active.is_(True),
        )
        if category:
            stmt = stmt.where(AudioPrompt.category == category)
        if site_id:
            stmt = stmt.where(AudioPrompt.site_id == site_id)
        stmt = stmt.order_by(AudioPrompt.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_prompt(
        self, tenant_id: uuid.UUID, prompt_id: uuid.UUID
    ) -> AudioPrompt | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(AudioPrompt).where(
                AudioPrompt.id == prompt_id,
                AudioPrompt.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_prompt(
        self,
        tenant_id: uuid.UUID,
        tenant_slug: str,
        name: str,
        category: str,
        description: str | None,
        file_data: bytes,
        filename: str,
    ) -> AudioPrompt:
        await set_tenant_context(self.db, tenant_id)

        # Check for duplicate name
        existing = await self.db.execute(
            select(AudioPrompt).where(
                AudioPrompt.tenant_id == tenant_id,
                AudioPrompt.name == name,
                AudioPrompt.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Audio prompt '{name}' already exists")

        prompt_id = uuid.uuid4()
        ext = os.path.splitext(filename)[1].lstrip(".") or "wav"
        sha256 = hashlib.sha256(file_data).hexdigest()

        # Storage paths
        object_name = f"prompts/{tenant_slug}/{prompt_id}.{ext}"
        local_dir = f"/recordings/prompts/{tenant_slug}"
        local_path = f"{local_dir}/{prompt_id}.{ext}"

        # Upload to MinIO
        uploaded = False
        if self.storage:
            content_type = "audio/wav" if ext == "wav" else f"audio/{ext}"
            uploaded = self.storage.upload_bytes(object_name, file_data, content_type)

        # Write to shared volume for FreeSWITCH access
        try:
            os.makedirs(local_dir, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_data)
        except OSError:
            local_path = None

        prompt = AudioPrompt(
            id=prompt_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            category=category,
            storage_path=object_name if uploaded else None,
            storage_bucket="recordings" if uploaded else None,
            file_size_bytes=len(file_data),
            format=ext,
            sha256_hash=sha256,
            local_path=local_path,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def get_playback_url(
        self, tenant_id: uuid.UUID, prompt_id: uuid.UUID
    ) -> str | None:
        prompt = await self.get_prompt(tenant_id, prompt_id)
        if not prompt or not prompt.storage_path or not self.storage:
            return None
        return self.storage.presigned_url(prompt.storage_path)

    async def soft_delete(
        self, tenant_id: uuid.UUID, prompt_id: uuid.UUID
    ) -> AudioPrompt | None:
        prompt = await self.get_prompt(tenant_id, prompt_id)
        if not prompt:
            return None
        prompt.is_active = False
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
