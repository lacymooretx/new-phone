import json
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.db.rls import set_tenant_context
from new_phone.models.did import DID, DIDStatus
from new_phone.models.sip_trunk import SIPTrunk, TrunkAuthType, TrunkTransport
from new_phone.providers.base import ClearlyIPLocationConfig, TrunkProvisionRequest, TrunkTestResult
from new_phone.providers.factory import get_clearlyip_provider, get_provider_for_tenant
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

        provider = await get_provider_for_tenant(self.db, tenant_id, provider_type)
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
            provider = await get_provider_for_tenant(self.db, tenant_id, trunk.provider_type)
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

        provider = await get_provider_for_tenant(self.db, tenant_id, trunk.provider_type)
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

    # ------------------------------------------------------------------
    # ClearlyIP keycode activation
    # ------------------------------------------------------------------

    async def activate_clearlyip_keycode(
        self,
        tenant_id: uuid.UUID,
        keycode: str,
        name_prefix: str = "ClearlyIP",
        import_dids: bool = True,
    ) -> dict:
        """Activate a ClearlyIP location via keycode and create trunks + DIDs.

        Returns a dict with primary_trunk_id, secondary_trunk_id,
        imported_dids, and location_name.
        """
        await set_tenant_context(self.db, tenant_id)

        provider = get_clearlyip_provider()
        logger.info(
            "clearlyip_activation_start",
            tenant_id=str(tenant_id),
            name_prefix=name_prefix,
        )

        config = await provider.fetch_location_config(keycode)

        # Create primary trunk
        primary_encrypted_pw = encrypt_value(config.sip_password) if config.sip_password else None
        primary_trunk = SIPTrunk(
            tenant_id=tenant_id,
            name=f"{name_prefix} - {config.location_name} (Primary)",
            auth_type=TrunkAuthType.REGISTRATION,
            host=config.primary_server,
            port=config.primary_port,
            username=config.sip_username,
            encrypted_password=primary_encrypted_pw,
            max_channels=0,  # ClearlyIP manages channel limits
            transport=TrunkTransport.TLS,
            provider_type="clearlyip",
            provider_trunk_id=f"clearlyip-{config.location_name}",
        )
        self.db.add(primary_trunk)
        await self.db.flush()  # Get primary_trunk.id for failover link

        # Create secondary trunk (if secondary server provided)
        secondary_trunk = None
        if config.secondary_server:
            secondary_trunk = SIPTrunk(
                tenant_id=tenant_id,
                name=f"{name_prefix} - {config.location_name} (Secondary)",
                auth_type=TrunkAuthType.REGISTRATION,
                host=config.secondary_server,
                port=config.secondary_port,
                username=config.sip_username,
                encrypted_password=primary_encrypted_pw,
                max_channels=0,
                transport=TrunkTransport.TLS,
                provider_type="clearlyip",
                provider_trunk_id=f"clearlyip-{config.location_name}-secondary",
            )
            self.db.add(secondary_trunk)
            await self.db.flush()

            # Link primary -> secondary via failover
            primary_trunk.failover_trunk_id = secondary_trunk.id

        # Store keycode in TelephonyProviderConfig for SMS/Fax re-use
        await self._store_clearlyip_keycode(tenant_id, keycode, config.location_name)

        # Import DIDs if requested
        imported_dids: list[str] = []
        if import_dids and config.dids:
            for number in config.dids:
                if not number:
                    continue
                # Check if DID already exists
                existing = await self.db.execute(
                    select(DID).where(DID.number == number)
                )
                if existing.scalar_one_or_none():
                    logger.debug("clearlyip_did_exists", number=number)
                    continue

                did = DID(
                    tenant_id=tenant_id,
                    number=number,
                    provider="clearlyip",
                    provider_sid=f"clearlyip-{number}",
                    status=DIDStatus.ACTIVE,
                )
                self.db.add(did)
                imported_dids.append(number)

        await self.db.commit()
        await self.db.refresh(primary_trunk)
        if secondary_trunk:
            await self.db.refresh(secondary_trunk)

        logger.info(
            "clearlyip_activation_complete",
            tenant_id=str(tenant_id),
            primary_trunk_id=str(primary_trunk.id),
            secondary_trunk_id=str(secondary_trunk.id) if secondary_trunk else None,
            dids_imported=len(imported_dids),
        )

        return {
            "primary_trunk_id": str(primary_trunk.id),
            "secondary_trunk_id": str(secondary_trunk.id) if secondary_trunk else None,
            "imported_dids": imported_dids,
            "location_name": config.location_name,
        }

    async def refresh_clearlyip(self, tenant_id: uuid.UUID) -> dict:
        """Re-fetch ClearlyIP config and sync trunks + DIDs.

        Returns a dict with trunks_updated, dids_added, dids_removed,
        credentials_changed.
        """
        await set_tenant_context(self.db, tenant_id)

        # Get stored keycode
        keycode = await self._get_stored_clearlyip_keycode(tenant_id)
        if not keycode:
            raise ValueError(
                "No ClearlyIP keycode stored for this tenant. "
                "Activate a keycode first."
            )

        provider = get_clearlyip_provider()
        config = await provider.fetch_location_config(keycode)

        # Find existing ClearlyIP trunks
        result = await self.db.execute(
            select(SIPTrunk).where(
                SIPTrunk.tenant_id == tenant_id,
                SIPTrunk.provider_type == "clearlyip",
                SIPTrunk.is_active.is_(True),
            )
        )
        trunks = list(result.scalars().all())

        trunks_updated = 0
        credentials_changed = False

        for trunk in trunks:
            changed = False
            # Update credentials if they changed
            new_encrypted_pw = encrypt_value(config.sip_password) if config.sip_password else None
            if trunk.username != config.sip_username:
                trunk.username = config.sip_username
                changed = True
                credentials_changed = True

            # Always update password (can't compare encrypted values easily)
            trunk.encrypted_password = new_encrypted_pw
            changed = True

            # Update host if it's the primary or secondary
            is_secondary = "secondary" in (trunk.provider_trunk_id or "").lower()
            expected_host = config.secondary_server if is_secondary else config.primary_server
            expected_port = config.secondary_port if is_secondary else config.primary_port

            if trunk.host != expected_host and expected_host:
                trunk.host = expected_host
                changed = True
            if trunk.port != expected_port:
                trunk.port = expected_port
                changed = True

            if changed:
                trunks_updated += 1

        # Diff DIDs
        existing_dids_result = await self.db.execute(
            select(DID).where(
                DID.tenant_id == tenant_id,
                DID.provider == "clearlyip",
                DID.is_active.is_(True),
            )
        )
        existing_dids = {d.number for d in existing_dids_result.scalars().all()}
        remote_dids = {n for n in config.dids if n}

        dids_added: list[str] = []
        for number in remote_dids - existing_dids:
            # Check global uniqueness
            existing = await self.db.execute(select(DID).where(DID.number == number))
            if existing.scalar_one_or_none():
                continue
            did = DID(
                tenant_id=tenant_id,
                number=number,
                provider="clearlyip",
                provider_sid=f"clearlyip-{number}",
                status=DIDStatus.ACTIVE,
            )
            self.db.add(did)
            dids_added.append(number)

        dids_removed: list[str] = list(existing_dids - remote_dids)
        # Flag removed DIDs (don't delete — just log for awareness)
        if dids_removed:
            logger.warning(
                "clearlyip_dids_removed_from_location",
                tenant_id=str(tenant_id),
                removed=dids_removed,
            )

        await self.db.commit()

        logger.info(
            "clearlyip_refresh_complete",
            tenant_id=str(tenant_id),
            trunks_updated=trunks_updated,
            dids_added=len(dids_added),
            dids_removed=len(dids_removed),
        )

        return {
            "trunks_updated": trunks_updated,
            "dids_added": dids_added,
            "dids_removed": dids_removed,
            "credentials_changed": credentials_changed,
        }

    # ------------------------------------------------------------------
    # ClearlyIP keycode storage helpers
    # ------------------------------------------------------------------

    async def _store_clearlyip_keycode(
        self, tenant_id: uuid.UUID, keycode: str, location_name: str
    ) -> None:
        """Store/update the ClearlyIP keycode in TelephonyProviderConfig."""
        from new_phone.models.telephony_provider_config import TelephonyProviderConfig

        # Check if one already exists
        result = await self.db.execute(
            select(TelephonyProviderConfig).where(
                TelephonyProviderConfig.tenant_id == tenant_id,
                TelephonyProviderConfig.provider_type == "clearlyip",
                TelephonyProviderConfig.is_active.is_(True),
            )
        )
        existing = result.scalar_one_or_none()

        encrypted_creds = encrypt_value(json.dumps({"keycode": keycode}))

        if existing:
            existing.encrypted_credentials = encrypted_creds
            existing.label = f"ClearlyIP - {location_name}"
        else:
            config = TelephonyProviderConfig(
                tenant_id=tenant_id,
                provider_type="clearlyip",
                label=f"ClearlyIP - {location_name}",
                encrypted_credentials=encrypted_creds,
                is_default=True,
            )
            self.db.add(config)

    async def _get_stored_clearlyip_keycode(self, tenant_id: uuid.UUID) -> str | None:
        """Retrieve the stored ClearlyIP keycode for a tenant."""
        from new_phone.models.telephony_provider_config import TelephonyProviderConfig

        # Check tenant-level first
        result = await self.db.execute(
            select(TelephonyProviderConfig).where(
                TelephonyProviderConfig.tenant_id == tenant_id,
                TelephonyProviderConfig.provider_type == "clearlyip",
                TelephonyProviderConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            # Check MSP-level
            result = await self.db.execute(
                select(TelephonyProviderConfig).where(
                    TelephonyProviderConfig.tenant_id.is_(None),
                    TelephonyProviderConfig.provider_type == "clearlyip",
                    TelephonyProviderConfig.is_active.is_(True),
                )
            )
            config = result.scalar_one_or_none()

        if not config:
            # Fall back to env var
            from new_phone.config import settings

            return settings.clearlyip_keycode or None

        creds = json.loads(decrypt_value(config.encrypted_credentials))
        return creds.get("keycode")
