import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.stir_shaken import (
    SpamAllowList,
    SpamBlockList,
    SpamFilter,
    StirShakenConfig,
)
from new_phone.schemas.stir_shaken import (
    NumberCheckResult,
    SpamAllowListCreate,
    SpamBlockListCreate,
    SpamFilterCreate,
    SpamFilterUpdate,
    StirShakenConfigCreate,
    StirShakenConfigUpdate,
)


class StirShakenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── STIR/SHAKEN Config ──

    async def get_config(self, tenant_id: uuid.UUID) -> StirShakenConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(StirShakenConfig).where(
                StirShakenConfig.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, tenant_id: uuid.UUID, data: StirShakenConfigCreate
    ) -> StirShakenConfig:
        await set_tenant_context(self.db, tenant_id)
        config = StirShakenConfig(tenant_id=tenant_id, **data.model_dump())
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(
        self, tenant_id: uuid.UUID, data: StirShakenConfigUpdate
    ) -> StirShakenConfig:
        config = await self.get_config(tenant_id)
        if not config:
            raise ValueError("STIR/SHAKEN config not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, tenant_id: uuid.UUID) -> None:
        await set_tenant_context(self.db, tenant_id)
        await self.db.execute(
            delete(StirShakenConfig).where(
                StirShakenConfig.tenant_id == tenant_id
            )
        )
        await self.db.commit()

    # ── Spam Filters ──

    async def list_spam_filters(self, tenant_id: uuid.UUID) -> list[SpamFilter]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamFilter)
            .where(SpamFilter.tenant_id == tenant_id)
            .order_by(SpamFilter.name)
        )
        return list(result.scalars().unique().all())

    async def get_spam_filter(
        self, tenant_id: uuid.UUID, filter_id: uuid.UUID
    ) -> SpamFilter | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamFilter).where(
                SpamFilter.id == filter_id, SpamFilter.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_spam_filter(
        self, tenant_id: uuid.UUID, data: SpamFilterCreate
    ) -> SpamFilter:
        await set_tenant_context(self.db, tenant_id)
        spam_filter = SpamFilter(tenant_id=tenant_id, **data.model_dump())
        self.db.add(spam_filter)
        await self.db.commit()
        await self.db.refresh(spam_filter)
        return spam_filter

    async def update_spam_filter(
        self, tenant_id: uuid.UUID, filter_id: uuid.UUID, data: SpamFilterUpdate
    ) -> SpamFilter:
        spam_filter = await self.get_spam_filter(tenant_id, filter_id)
        if not spam_filter:
            raise ValueError("Spam filter not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(spam_filter, key, value)
        await self.db.commit()
        await self.db.refresh(spam_filter)
        return spam_filter

    async def delete_spam_filter(
        self, tenant_id: uuid.UUID, filter_id: uuid.UUID
    ) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamFilter).where(
                SpamFilter.id == filter_id, SpamFilter.tenant_id == tenant_id
            )
        )
        spam_filter = result.scalar_one_or_none()
        if not spam_filter:
            raise ValueError("Spam filter not found")
        await self.db.execute(
            delete(SpamFilter).where(SpamFilter.id == filter_id)
        )
        await self.db.commit()

    # ── Spam Block List ──

    async def list_blocked_numbers(
        self, tenant_id: uuid.UUID
    ) -> list[SpamBlockList]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamBlockList)
            .where(SpamBlockList.tenant_id == tenant_id)
            .order_by(SpamBlockList.blocked_at.desc())
        )
        return list(result.scalars().unique().all())

    async def add_blocked_number(
        self, tenant_id: uuid.UUID, data: SpamBlockListCreate
    ) -> SpamBlockList:
        await set_tenant_context(self.db, tenant_id)
        entry = SpamBlockList(
            tenant_id=tenant_id,
            phone_number=data.phone_number,
            reason=data.reason,
            blocked_at=data.blocked_at or datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def remove_blocked_number(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID
    ) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamBlockList).where(
                SpamBlockList.id == entry_id, SpamBlockList.tenant_id == tenant_id
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Blocked number not found")
        await self.db.execute(
            delete(SpamBlockList).where(SpamBlockList.id == entry_id)
        )
        await self.db.commit()

    # ── Spam Allow List ──

    async def list_allowed_numbers(
        self, tenant_id: uuid.UUID
    ) -> list[SpamAllowList]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamAllowList)
            .where(SpamAllowList.tenant_id == tenant_id)
            .order_by(SpamAllowList.phone_number)
        )
        return list(result.scalars().unique().all())

    async def add_allowed_number(
        self, tenant_id: uuid.UUID, data: SpamAllowListCreate
    ) -> SpamAllowList:
        await set_tenant_context(self.db, tenant_id)
        entry = SpamAllowList(
            tenant_id=tenant_id,
            phone_number=data.phone_number,
            label=data.label,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def remove_allowed_number(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID
    ) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SpamAllowList).where(
                SpamAllowList.id == entry_id, SpamAllowList.tenant_id == tenant_id
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Allowed number not found")
        await self.db.execute(
            delete(SpamAllowList).where(SpamAllowList.id == entry_id)
        )
        await self.db.commit()

    # ── Number Check ──

    async def check_number(
        self, tenant_id: uuid.UUID, phone_number: str
    ) -> NumberCheckResult:
        await set_tenant_context(self.db, tenant_id)

        # Check block list
        block_result = await self.db.execute(
            select(SpamBlockList).where(
                SpamBlockList.tenant_id == tenant_id,
                SpamBlockList.phone_number == phone_number,
            )
        )
        is_blocked = block_result.scalar_one_or_none() is not None

        # Check allow list
        allow_result = await self.db.execute(
            select(SpamAllowList).where(
                SpamAllowList.tenant_id == tenant_id,
                SpamAllowList.phone_number == phone_number,
            )
        )
        is_allowed = allow_result.scalar_one_or_none() is not None

        # Calculate spam score from active filters
        spam_score: int | None = None
        if not is_allowed:
            filters_result = await self.db.execute(
                select(SpamFilter).where(
                    SpamFilter.tenant_id == tenant_id,
                    SpamFilter.is_active.is_(True),
                )
            )
            filters = list(filters_result.scalars().unique().all())
            if filters:
                # Use the lowest spam_score_threshold from matching filters
                # as a baseline indicator; real scoring would integrate with
                # external STIR/SHAKEN verification results.
                spam_score = min(f.spam_score_threshold for f in filters)

        return NumberCheckResult(
            is_blocked=is_blocked,
            is_allowed=is_allowed,
            spam_score=spam_score,
        )
