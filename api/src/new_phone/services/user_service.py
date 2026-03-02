import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.passwords import hash_password
from new_phone.db.rls import set_tenant_context
from new_phone.models.user import User
from new_phone.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, tenant_id: uuid.UUID) -> list[User]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id).order_by(User.email)
        )
        return list(result.scalars().all())

    async def get_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, tenant_id: uuid.UUID, data: UserCreate) -> User:
        existing = await self.get_user_by_email(data.email)
        if existing:
            raise ValueError(f"User with email '{data.email}' already exists")

        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get_user(tenant_id, user_id)
        if not user:
            raise ValueError("User not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def deactivate_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
        user = await self.get_user(tenant_id, user_id)
        if not user:
            raise ValueError("User not found")

        user.is_active = False
        user.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        return user
