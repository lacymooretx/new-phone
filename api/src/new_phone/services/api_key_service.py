import hashlib
import secrets
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.api_key import ApiKey

logger = structlog.get_logger()

KEY_PREFIX = "np_"


def _generate_key() -> tuple[str, str, str]:
    """Generate API key, return (raw_key, key_prefix, key_hash)."""
    random_part = secrets.token_hex(24)
    raw_key = f"{KEY_PREFIX}{random_part}"
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_prefix, key_hash


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class ApiKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_keys(self, tenant_id: uuid.UUID) -> list[ApiKey]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.tenant_id == tenant_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_key(self, tenant_id: uuid.UUID, key_id: uuid.UUID) -> ApiKey | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_key(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, *,
        name: str, scopes: list[str], rate_limit: int = 1000,
        description: str | None = None, expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key. Returns (key_model, raw_key). Raw key is only available at creation."""
        await set_tenant_context(self.db, tenant_id)
        raw_key, key_prefix, key_hash = _generate_key()
        api_key = ApiKey(
            tenant_id=tenant_id,
            created_by_user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            rate_limit=rate_limit,
            description=description,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(api_key)
        return api_key, raw_key

    async def update_key(self, tenant_id: uuid.UUID, key_id: uuid.UUID, **updates) -> ApiKey | None:
        key = await self.get_key(tenant_id, key_id)
        if not key:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(key, k):
                setattr(key, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(key)
        return key

    async def delete_key(self, tenant_id: uuid.UUID, key_id: uuid.UUID) -> bool:
        key = await self.get_key(tenant_id, key_id)
        if not key:
            return False
        await self.db.delete(key)
        await self.db.commit()
        return True

    async def validate_key(self, raw_key: str) -> ApiKey | None:
        """Validate an API key and return the key record if valid."""
        key_hash = _hash_key(raw_key)
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
            return None
        api_key.last_used_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.commit()
        return api_key
