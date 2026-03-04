import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.sip_trunk import SIPTrunk
from new_phone.models.tenant import Tenant
from new_phone.models.user import User
from new_phone.schemas.providers import (
    KeycodeActivateRequest,
    KeycodeActivateResult,
    KeycodeRefreshResult,
    TrunkProvisionRequestSchema,
    TrunkTestResultSchema,
)
from new_phone.schemas.sip_trunk import SIPTrunkCreate, SIPTrunkResponse, SIPTrunkUpdate
from new_phone.services.sip_trunk_service import SIPTrunkService

logger = structlog.get_logger()


async def _get_tenant(tenant_id: uuid.UUID) -> Tenant | None:
    """Load tenant by ID (admin session, bypasses RLS)."""
    from new_phone.db.engine import AdminSessionLocal

    async with AdminSessionLocal() as s:
        return (await s.execute(sa_select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()


def _build_gw_xml(trunk: SIPTrunkResponse | SIPTrunk, tenant: Tenant) -> tuple[str, str]:
    """Build gateway name and XML content for a trunk.

    Returns (gw_name, xml_content). xml_content may be empty if trunk has no host.
    """
    from new_phone.auth.encryption import decrypt_value
    from new_phone.freeswitch.xml_builder import build_gateway_file, gateway_fs_name

    gw_name = gateway_fs_name(tenant.slug, trunk.name)
    password = ""
    enc_pwd = getattr(trunk, "encrypted_password", None)
    if enc_pwd:
        try:
            password = decrypt_value(enc_pwd)
        except ValueError:
            pass
    xml = build_gateway_file(trunk, tenant, password)
    return gw_name, xml


async def _sync_gateway_create(trunk: SIPTrunk | None = None, tenant: Tenant | None = None) -> None:
    try:
        from new_phone.main import config_sync
        if not config_sync:
            return
        if trunk and tenant:
            gw_name, xml = _build_gw_xml(trunk, tenant)
            await config_sync.notify_gateway_create(gw_name, xml)
        else:
            await config_sync.notify_gateway_create()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


async def _sync_gateway_change(
    old_gw_name: str | None = None,
    trunk: SIPTrunk | None = None,
    tenant: Tenant | None = None,
) -> None:
    try:
        from new_phone.main import config_sync
        if not config_sync:
            return
        new_gw_name = None
        xml = None
        if trunk and tenant:
            new_gw_name, xml = _build_gw_xml(trunk, tenant)
        await config_sync.notify_gateway_change(old_gw_name, new_gw_name, xml)
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


async def _sync_gateway_delete(gw_name: str) -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_gateway_delete(gw_name)
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


async def _startup_gateway_sync() -> None:
    """Full gateway sync — loads all trunks from DB and writes gateway files."""
    from new_phone.auth.encryption import decrypt_value
    from new_phone.db.engine import AdminSessionLocal
    from new_phone.main import config_sync

    if not config_sync:
        return

    async with AdminSessionLocal() as session:
        trunks = list(
            (await session.execute(sa_select(SIPTrunk).where(SIPTrunk.is_active.is_(True))))
            .scalars()
            .all()
        )
        tenant_ids = {t.tenant_id for t in trunks}
        tenants_result = await session.execute(sa_select(Tenant).where(Tenant.id.in_(tenant_ids)))
        tenants = {str(t.id): t for t in tenants_result.scalars().all()}
        passwords = {}
        for trunk in trunks:
            if trunk.encrypted_password:
                try:
                    passwords[str(trunk.id)] = decrypt_value(trunk.encrypted_password)
                except ValueError:
                    pass
        await config_sync.sync_all_gateways(trunks, tenants, passwords)

router = APIRouter(prefix="/tenants/{tenant_id}/trunks", tags=["sip-trunks"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[SIPTrunkResponse])
async def list_trunks(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    return await service.list_trunks(tenant_id)


@router.post("", response_model=SIPTrunkResponse, status_code=status.HTTP_201_CREATED)
async def create_trunk(
    tenant_id: uuid.UUID,
    body: SIPTrunkCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    trunk = await service.create_trunk(tenant_id, body)
    tenant = await _get_tenant(tenant_id)
    # Reload the raw model for encrypted_password access
    from new_phone.db.engine import AdminSessionLocal

    async with AdminSessionLocal() as s:
        raw_trunk = (await s.execute(sa_select(SIPTrunk).where(SIPTrunk.id == trunk.id))).scalar_one_or_none()
        if raw_trunk and tenant:
            await _sync_gateway_create(raw_trunk, tenant)
    return trunk


@router.get("/{trunk_id}", response_model=SIPTrunkResponse)
async def get_trunk(
    tenant_id: uuid.UUID,
    trunk_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    trunk = await service.get_trunk(tenant_id, trunk_id)
    if not trunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SIP trunk not found")
    return trunk


@router.patch("/{trunk_id}", response_model=SIPTrunkResponse)
async def update_trunk(
    tenant_id: uuid.UUID,
    trunk_id: uuid.UUID,
    body: SIPTrunkUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        from new_phone.db.engine import AdminSessionLocal
        from new_phone.freeswitch.xml_builder import gateway_fs_name

        # Get old trunk name to kill the gateway
        old_trunk = await service.get_trunk(tenant_id, trunk_id)
        trunk = await service.update_trunk(tenant_id, trunk_id, body)
        tenant = await _get_tenant(tenant_id)
        if tenant and old_trunk:
            old_gw_name = gateway_fs_name(tenant.slug, old_trunk.name)
            async with AdminSessionLocal() as s:
                raw_trunk = (await s.execute(sa_select(SIPTrunk).where(SIPTrunk.id == trunk.id))).scalar_one_or_none()
                await _sync_gateway_change(old_gw_name, raw_trunk, tenant)
        return trunk
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{trunk_id}", response_model=SIPTrunkResponse)
async def deactivate_trunk(
    tenant_id: uuid.UUID,
    trunk_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        from new_phone.freeswitch.xml_builder import gateway_fs_name

        # Get trunk name for gateway kill
        trunk = await service.get_trunk(tenant_id, trunk_id)
        result = await service.deactivate_trunk(tenant_id, trunk_id)
        if trunk:
            tenant = await _get_tenant(tenant_id)
            if tenant:
                gw_name = gateway_fs_name(tenant.slug, trunk.name)
                await _sync_gateway_delete(gw_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ------------------------------------------------------------------
# Provider-backed provisioning endpoints
# ------------------------------------------------------------------


@router.post("/provision", response_model=SIPTrunkResponse, status_code=status.HTTP_201_CREATED)
async def provision_trunk(
    tenant_id: uuid.UUID,
    body: TrunkProvisionRequestSchema,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Provision a new SIP trunk via a telephony provider."""
    _check_tenant_access(user, tenant_id)

    if body.provider == "clearlyip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "ClearlyIP uses keycode-based activation, not standard provisioning. "
                "Use POST /tenants/{tenant_id}/trunks/activate-keycode instead."
            ),
        )

    service = SIPTrunkService(db)
    try:
        trunk = await service.provision(
            tenant_id,
            provider_type=body.provider,
            name=body.name,
            region=body.region,
            channels=body.channels,
            config=body.config,
        )
        tenant = await _get_tenant(tenant_id)
        from new_phone.db.engine import AdminSessionLocal

        async with AdminSessionLocal() as s:
            raw_trunk = (await s.execute(sa_select(SIPTrunk).where(SIPTrunk.id == trunk.id))).scalar_one_or_none()
            if raw_trunk and tenant:
                await _sync_gateway_create(raw_trunk, tenant)
        return trunk
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    except Exception as e:
        logger.error(
            "trunk_provision_failed",
            error=str(e),
            tenant_id=str(tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider provisioning failed: {e}",
        ) from None


@router.post("/{trunk_id}/deprovision", response_model=SIPTrunkResponse)
async def deprovision_trunk(
    tenant_id: uuid.UUID,
    trunk_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Deprovision a SIP trunk from the telephony provider and deactivate it."""
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        from new_phone.freeswitch.xml_builder import gateway_fs_name

        # For ClearlyIP trunks, just deactivate locally (no provider API)
        existing = await service.get_trunk(tenant_id, trunk_id)
        if existing and existing.provider_type == "clearlyip":
            trunk = await service.deactivate_trunk(tenant_id, trunk_id)
        else:
            trunk = await service.deprovision(tenant_id, trunk_id)
        if trunk:
            tenant = await _get_tenant(tenant_id)
            if tenant:
                gw_name = gateway_fs_name(tenant.slug, trunk.name)
                await _sync_gateway_delete(gw_name)
        return trunk
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/activate-keycode", response_model=KeycodeActivateResult, status_code=status.HTTP_201_CREATED)
async def activate_keycode(
    tenant_id: uuid.UUID,
    body: KeycodeActivateRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Activate a ClearlyIP location via keycode — creates trunks and imports DIDs."""
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        result = await service.activate_clearlyip_keycode(
            tenant_id,
            keycode=body.keycode,
            name_prefix=body.name_prefix,
            import_dids=body.import_dids,
        )
        # Sync all gateways (keycode may create multiple trunks)
        try:
            from new_phone.main import config_sync
            if config_sync:
                await _startup_gateway_sync()
        except Exception as e:
            logger.warning("config_sync_failed", error=str(e))
        return KeycodeActivateResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    except Exception as e:
        logger.error(
            "keycode_activation_failed",
            error=str(e),
            tenant_id=str(tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ClearlyIP keycode activation failed: {e}",
        ) from None


@router.post("/refresh-clearlyip", response_model=KeycodeRefreshResult)
async def refresh_clearlyip(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Re-fetch ClearlyIP config and sync trunks + DIDs."""
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        result = await service.refresh_clearlyip(tenant_id)
        return KeycodeRefreshResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    except Exception as e:
        logger.error(
            "clearlyip_refresh_failed",
            error=str(e),
            tenant_id=str(tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ClearlyIP refresh failed: {e}",
        ) from None


@router.post("/{trunk_id}/test", response_model=TrunkTestResultSchema)
async def test_trunk(
    tenant_id: uuid.UUID,
    trunk_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Run a SIP connectivity test against a trunk via its provider."""
    _check_tenant_access(user, tenant_id)
    service = SIPTrunkService(db)
    try:
        result = await service.test_trunk(tenant_id, trunk_id)
        return TrunkTestResultSchema(
            status=result.status,
            latency_ms=result.latency_ms,
            error=result.error,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
