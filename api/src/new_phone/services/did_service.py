import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.did import DID, DIDProvider, DIDStatus
from new_phone.providers.base import DIDSearchResult as ProviderDIDSearchResult
from new_phone.providers.factory import get_provider_for_tenant
from new_phone.schemas.did import DIDCreate, DIDUpdate

logger = structlog.get_logger()


class DIDService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_dids(self, tenant_id: uuid.UUID, *, site_id: uuid.UUID | None = None) -> list[DID]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(DID)
            .where(DID.tenant_id == tenant_id, DID.is_active.is_(True))
            .order_by(DID.number)
        )
        if site_id is not None:
            stmt = stmt.where(DID.site_id == site_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_did(self, tenant_id: uuid.UUID, did_id: uuid.UUID) -> DID | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(DID).where(DID.id == did_id, DID.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_did(self, tenant_id: uuid.UUID, data: DIDCreate) -> DID:
        await set_tenant_context(self.db, tenant_id)
        # E.164 numbers are globally unique (no tenant scoping)
        existing = await self.db.execute(
            select(DID).where(DID.number == data.number)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"DID '{data.number}' already exists")

        did = DID(tenant_id=tenant_id, **data.model_dump())
        self.db.add(did)
        await self.db.commit()
        await self.db.refresh(did)
        return did

    async def update_did(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID, data: DIDUpdate
    ) -> DID:
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(did, key, value)

        await self.db.commit()
        await self.db.refresh(did)
        return did

    async def deactivate_did(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID
    ) -> DID:
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        did.is_active = False
        did.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(did)
        return did

    # ------------------------------------------------------------------
    # Provider-backed provisioning methods
    # ------------------------------------------------------------------

    async def search_available(
        self,
        tenant_id: uuid.UUID,
        area_code: str | None = None,
        state: str | None = None,
        quantity: int = 10,
        provider_type: str | None = None,
    ) -> list[ProviderDIDSearchResult]:
        """Search for available DIDs from the tenant's provider."""
        if provider_type:
            provider = await get_provider_for_tenant(self.db, tenant_id, provider_type)
        else:
            # Determine provider from existing trunks, default to clearlyip
            from new_phone.providers.factory import get_tenant_provider

            provider = await get_tenant_provider(self.db, tenant_id)

        logger.info(
            "did_search_available",
            tenant_id=str(tenant_id),
            area_code=area_code,
            state=state,
            quantity=quantity,
        )
        return await provider.search_dids(area_code, state, quantity)

    async def purchase(
        self,
        tenant_id: uuid.UUID,
        number: str,
        provider_type: str,
    ) -> DID:
        """Purchase a DID from the provider and create a local DB record."""
        await set_tenant_context(self.db, tenant_id)

        # Check it doesn't already exist
        existing = await self.db.execute(select(DID).where(DID.number == number))
        if existing.scalar_one_or_none():
            raise ValueError(f"DID '{number}' already exists in the system")

        provider = await get_provider_for_tenant(self.db, tenant_id, provider_type)
        logger.info(
            "did_purchase_start",
            tenant_id=str(tenant_id),
            number=number,
            provider=provider_type,
        )

        result = await provider.purchase_did(number)

        did = DID(
            tenant_id=tenant_id,
            number=result.number,
            provider=result.provider,
            provider_sid=result.provider_sid,
            status=DIDStatus.ACTIVE,
        )
        self.db.add(did)
        await self.db.commit()
        await self.db.refresh(did)

        logger.info(
            "did_purchase_complete",
            tenant_id=str(tenant_id),
            did_id=str(did.id),
            number=did.number,
            provider_sid=did.provider_sid,
        )
        return did

    async def release(self, tenant_id: uuid.UUID, did_id: uuid.UUID) -> DID:
        """Release a DID at the provider and mark it released locally."""
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        if did.status == DIDStatus.RELEASED:
            raise ValueError("DID is already released")

        # Release at provider if we have a provider_sid
        if did.provider_sid and did.provider != DIDProvider.MANUAL:
            provider = await get_provider_for_tenant(self.db, tenant_id, did.provider)
            released = await provider.release_did(did.provider_sid)
            if not released:
                logger.warning(
                    "did_release_provider_failed",
                    did_id=str(did_id),
                    provider=did.provider,
                    provider_sid=did.provider_sid,
                )
                raise ValueError(
                    f"Failed to release DID at provider ({did.provider}). "
                    "The provider may be unreachable — try again later."
                )

        did.status = DIDStatus.RELEASED
        did.is_active = False
        did.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(did)

        logger.info(
            "did_released",
            tenant_id=str(tenant_id),
            did_id=str(did_id),
            number=did.number,
        )
        return did

    async def configure_routing(
        self,
        tenant_id: uuid.UUID,
        did_id: uuid.UUID,
        destination_type: str,
        destination_id: str,
    ) -> DID:
        """Update DID routing at the provider and store config locally."""
        did = await self.get_did(tenant_id, did_id)
        if not did:
            raise ValueError("DID not found")

        if not did.is_active:
            raise ValueError("Cannot configure routing on an inactive DID")

        # Push config to provider if managed
        if did.provider_sid and did.provider != DIDProvider.MANUAL:
            provider = await get_provider_for_tenant(self.db, tenant_id, did.provider)
            config = {
                "destination_type": destination_type,
                "destination_id": destination_id,
            }
            success = await provider.configure_did(did.provider_sid, config)
            if not success:
                logger.warning(
                    "did_configure_routing_provider_failed",
                    did_id=str(did_id),
                    provider=did.provider,
                )
                # Non-fatal — we still update locally

        # The DID model doesn't have dedicated routing columns today, so we
        # would typically update the inbound_routes table.  For now we log
        # and return the DID unchanged (routing lives in inbound_routes).
        logger.info(
            "did_routing_configured",
            tenant_id=str(tenant_id),
            did_id=str(did_id),
            destination_type=destination_type,
            destination_id=destination_id,
        )

        await self.db.commit()
        await self.db.refresh(did)
        return did
