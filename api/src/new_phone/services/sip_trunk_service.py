import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.db.rls import set_tenant_context
from new_phone.models.sip_trunk import SIPTrunk, TrunkAuthType, TrunkTransport
from new_phone.providers.base import TrunkProvisionRequest, TrunkTestResult
from new_phone.providers.factory import get_provider
from new_phone.schemas.sip_trunk import SIPTrunkCreate, SIPTrunkUpdate

logger = structlog.get_logger()


class SIPTrunkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_trunks(self, tenant_id: uuid.UUID) -> list[SIPTrunk]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SIPTrunk)
            .where(SIPTrunk.tenant_id == tenant_id, SIPTrunk.is_active.is_(True))
            .order_by(SIPTrunk.name)
        )
        return list(result.scalars().all())

    async def get_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> SIPTrunk | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SIPTrunk).where(
                SIPTrunk.id == trunk_id, SIPTrunk.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_trunk(
        self, tenant_id: uuid.UUID, data: SIPTrunkCreate
    ) -> SIPTrunk:
        await set_tenant_context(self.db, tenant_id)
        trunk_data = data.model_dump(exclude={"password"})

        # Encrypt password if provided
        encrypted_pw = None
        if data.password:
            encrypted_pw = encrypt_value(data.password)

        trunk = SIPTrunk(
            tenant_id=tenant_id,
            encrypted_password=encrypted_pw,
            **trunk_data,
        )
        self.db.add(trunk)
        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk

    async def update_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID, data: SIPTrunkUpdate
    ) -> SIPTrunk:
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})
        for key, value in update_data.items():
            setattr(trunk, key, value)

        # Handle password separately — encrypt it
        if data.password is not None:
            trunk.encrypted_password = encrypt_value(data.password)

        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk

    async def deactivate_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> SIPTrunk:
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        trunk.is_active = False
        trunk.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(trunk)
        return trunk

    # ------------------------------------------------------------------
    # Provider-backed provisioning methods
    # ------------------------------------------------------------------

    async def provision(
        self,
        tenant_id: uuid.UUID,
        provider_type: str,
        name: str,
        region: str = "us-east",
        channels: int = 30,
        config: dict | None = None,
    ) -> SIPTrunk:
        """Create a trunk at the provider and persist a local DB record."""
        await set_tenant_context(self.db, tenant_id)

        provider = get_provider(provider_type)
        provision_req = TrunkProvisionRequest(
            name=name,
            provider=provider_type,
            region=region,
            channels=channels,
            config=config or {},
        )

        logger.info(
            "trunk_provision_start",
            tenant_id=str(tenant_id),
            provider=provider_type,
            name=name,
        )

        result = await provider.create_trunk(provision_req)

        # Encrypt the provider-generated password
        encrypted_pw = None
        if result.password:
            encrypted_pw = encrypt_value(result.password)

        trunk = SIPTrunk(
            tenant_id=tenant_id,
            name=name,
            auth_type=TrunkAuthType.REGISTRATION,
            host=result.host,
            port=result.port,
            username=result.username,
            encrypted_password=encrypted_pw,
            max_channels=channels,
            transport=TrunkTransport.TLS,
            provider_type=provider_type,
            provider_trunk_id=result.provider_trunk_id,
        )
        self.db.add(trunk)
        await self.db.commit()
        await self.db.refresh(trunk)

        logger.info(
            "trunk_provision_complete",
            tenant_id=str(tenant_id),
            trunk_id=str(trunk.id),
            provider_trunk_id=result.provider_trunk_id,
        )
        return trunk

    async def deprovision(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> SIPTrunk:
        """Delete the trunk at the provider and deactivate locally."""
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        # Delete at provider if we have a provider_trunk_id
        if trunk.provider_trunk_id and trunk.provider_type:
            provider = get_provider(trunk.provider_type)
            deleted = await provider.delete_trunk(trunk.provider_trunk_id)
            if not deleted:
                logger.warning(
                    "trunk_deprovision_provider_failed",
                    trunk_id=str(trunk_id),
                    provider=trunk.provider_type,
                    provider_trunk_id=trunk.provider_trunk_id,
                )
                raise ValueError(
                    f"Failed to delete trunk at provider ({trunk.provider_type}). "
                    "The provider may be unreachable — try again later."
                )

        trunk.is_active = False
        trunk.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(trunk)

        logger.info(
            "trunk_deprovisioned",
            tenant_id=str(tenant_id),
            trunk_id=str(trunk_id),
        )
        return trunk

    async def test_trunk(
        self, tenant_id: uuid.UUID, trunk_id: uuid.UUID
    ) -> TrunkTestResult:
        """Run a SIP OPTIONS / connectivity test against the trunk's provider."""
        trunk = await self.get_trunk(tenant_id, trunk_id)
        if not trunk:
            raise ValueError("SIP trunk not found")

        if not trunk.provider_trunk_id or not trunk.provider_type:
            return TrunkTestResult(
                status="skipped",
                latency_ms=None,
                error="Trunk is not provider-managed — no remote test available",
            )

        provider = get_provider(trunk.provider_type)
        logger.info(
            "trunk_test_start",
            tenant_id=str(tenant_id),
            trunk_id=str(trunk_id),
            provider=trunk.provider_type,
        )
        result = await provider.test_trunk(trunk.provider_trunk_id)
        logger.info(
            "trunk_test_complete",
            tenant_id=str(tenant_id),
            trunk_id=str(trunk_id),
            status=result.status,
            latency_ms=result.latency_ms,
        )
        return result
