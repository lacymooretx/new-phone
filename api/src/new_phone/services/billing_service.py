import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.billing import BillingConfig, RateDeck, RateDeckEntry, UsageRecord

logger = structlog.get_logger()


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Usage Records ─────────────────────────────────────

    async def list_usage_records(
        self,
        tenant_id: uuid.UUID,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        metric: str | None = None,
    ) -> list[UsageRecord]:
        await set_tenant_context(self.db, tenant_id)
        query = select(UsageRecord).where(UsageRecord.tenant_id == tenant_id)

        if period_start:
            query = query.where(UsageRecord.period_start >= period_start)
        if period_end:
            query = query.where(UsageRecord.period_end <= period_end)
        if metric:
            query = query.where(UsageRecord.metric == metric)

        query = query.order_by(UsageRecord.period_start.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_usage_record(self, tenant_id: uuid.UUID, **kwargs) -> UsageRecord:
        await set_tenant_context(self.db, tenant_id)
        record = UsageRecord(tenant_id=tenant_id, **kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ── Rate Decks ────────────────────────────────────────

    async def list_rate_decks(self, tenant_id: uuid.UUID) -> list[RateDeck]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(RateDeck)
            .where(RateDeck.tenant_id == tenant_id)
            .order_by(RateDeck.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_rate_deck(self, tenant_id: uuid.UUID, **kwargs) -> RateDeck:
        await set_tenant_context(self.db, tenant_id)
        deck = RateDeck(tenant_id=tenant_id, **kwargs)
        self.db.add(deck)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(deck)
        return deck

    async def get_rate_deck(self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID) -> RateDeck | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(RateDeck).where(
                RateDeck.id == rate_deck_id,
                RateDeck.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_rate_deck(
        self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID, **updates
    ) -> RateDeck | None:
        deck = await self.get_rate_deck(tenant_id, rate_deck_id)
        if not deck:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(deck, k):
                setattr(deck, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(deck)
        return deck

    async def delete_rate_deck(self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID) -> bool:
        deck = await self.get_rate_deck(tenant_id, rate_deck_id)
        if not deck:
            return False
        await self.db.delete(deck)
        await self.db.commit()
        return True

    # ── Rate Deck Entries ─────────────────────────────────

    async def list_rate_deck_entries(
        self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID
    ) -> list[RateDeckEntry]:
        # Verify the rate deck belongs to this tenant
        deck = await self.get_rate_deck(tenant_id, rate_deck_id)
        if not deck:
            return []
        result = await self.db.execute(
            select(RateDeckEntry)
            .where(RateDeckEntry.rate_deck_id == rate_deck_id)
            .order_by(RateDeckEntry.prefix)
        )
        return list(result.scalars().all())

    async def create_rate_deck_entry(
        self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID, **kwargs
    ) -> RateDeckEntry:
        deck = await self.get_rate_deck(tenant_id, rate_deck_id)
        if not deck:
            raise ValueError("Rate deck not found")
        entry = RateDeckEntry(rate_deck_id=rate_deck_id, **kwargs)
        self.db.add(entry)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_rate_deck_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(RateDeckEntry).where(RateDeckEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return False
        # Verify ownership via rate deck
        deck = await self.get_rate_deck(tenant_id, entry.rate_deck_id)
        if not deck:
            return False
        await self.db.delete(entry)
        await self.db.commit()
        return True

    async def lookup_rate(
        self, tenant_id: uuid.UUID, rate_deck_id: uuid.UUID, dialed_number: str
    ) -> RateDeckEntry | None:
        """Find the longest prefix match for a dialed number."""
        deck = await self.get_rate_deck(tenant_id, rate_deck_id)
        if not deck:
            raise ValueError("Rate deck not found")

        result = await self.db.execute(
            select(RateDeckEntry)
            .where(RateDeckEntry.rate_deck_id == rate_deck_id)
            .order_by(RateDeckEntry.prefix.desc())
        )
        entries = list(result.scalars().all())

        # Longest prefix match
        best_match: RateDeckEntry | None = None
        best_len = 0
        for entry in entries:
            if dialed_number.startswith(entry.prefix) and len(entry.prefix) > best_len:
                best_match = entry
                best_len = len(entry.prefix)

        return best_match

    # ── Billing Config ────────────────────────────────────

    async def get_billing_config(self, tenant_id: uuid.UUID) -> BillingConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(BillingConfig).where(BillingConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_billing_config(self, tenant_id: uuid.UUID, **updates) -> BillingConfig:
        await set_tenant_context(self.db, tenant_id)
        config = await self.get_billing_config(tenant_id)
        if not config:
            # Auto-create config on first update
            config = BillingConfig(tenant_id=tenant_id, **updates)
            self.db.add(config)
        else:
            for k, v in updates.items():
                if v is not None and hasattr(config, k):
                    setattr(config, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(config)
        return config
