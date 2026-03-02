import secrets
import string
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.auth.passwords import hash_password
from new_phone.db.rls import set_tenant_context
from new_phone.models.extension import Extension
from new_phone.schemas.extension import ExtensionCreate, ExtensionUpdate


def _generate_sip_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_sip_username(tenant_id: uuid.UUID, ext_number: str) -> str:
    short_tid = str(tenant_id)[:8]
    return f"{short_tid}-{ext_number}"


class ExtensionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_extensions(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[Extension]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(Extension)
            .where(Extension.tenant_id == tenant_id, Extension.is_active.is_(True))
            .order_by(Extension.extension_number)
        )
        if site_id is not None:
            stmt = stmt.where(Extension.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_extension(
        self, tenant_id: uuid.UUID, ext_id: uuid.UUID
    ) -> Extension | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Extension).where(
                Extension.id == ext_id, Extension.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_extension(
        self, tenant_id: uuid.UUID, data: ExtensionCreate
    ) -> Extension:
        await set_tenant_context(self.db, tenant_id)
        # Check duplicate extension number in tenant
        existing = await self.db.execute(
            select(Extension).where(
                Extension.tenant_id == tenant_id,
                Extension.extension_number == data.extension_number,
                Extension.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Extension '{data.extension_number}' already exists in this tenant"
            )

        sip_password = _generate_sip_password()
        sip_username = _generate_sip_username(tenant_id, data.extension_number)

        ext_data = data.model_dump()
        ext = Extension(
            tenant_id=tenant_id,
            sip_username=sip_username,
            sip_password_hash=hash_password(sip_password),
            encrypted_sip_password=encrypt_value(sip_password),
            **ext_data,
        )
        self.db.add(ext)
        await self.db.commit()
        await self.db.refresh(ext)
        return ext

    async def update_extension(
        self, tenant_id: uuid.UUID, ext_id: uuid.UUID, data: ExtensionUpdate
    ) -> Extension:
        ext = await self.get_extension(tenant_id, ext_id)
        if not ext:
            raise ValueError("Extension not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ext, key, value)

        await self.db.commit()
        await self.db.refresh(ext)
        return ext

    async def deactivate_extension(
        self, tenant_id: uuid.UUID, ext_id: uuid.UUID
    ) -> Extension:
        ext = await self.get_extension(tenant_id, ext_id)
        if not ext:
            raise ValueError("Extension not found")

        ext.is_active = False
        ext.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(ext)
        return ext

    async def reset_sip_password(
        self, tenant_id: uuid.UUID, ext_id: uuid.UUID
    ) -> str:
        ext = await self.get_extension(tenant_id, ext_id)
        if not ext:
            raise ValueError("Extension not found")

        new_password = _generate_sip_password()
        ext.sip_password_hash = hash_password(new_password)
        ext.encrypted_sip_password = encrypt_value(new_password)
        await self.db.commit()
        return new_password
