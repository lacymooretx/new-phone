import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.sip_trunk import SIPTrunkCreate, SIPTrunkResponse, SIPTrunkUpdate
from new_phone.services.sip_trunk_service import SIPTrunkService

logger = structlog.get_logger()


async def _sync_gateway_create() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_gateway_create()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


async def _sync_gateway_change(gateway_name: str | None = None) -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_gateway_change(gateway_name)
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

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
    await _sync_gateway_create()
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
        # Get old trunk name to kill the gateway
        old_trunk = await service.get_trunk(tenant_id, trunk_id)
        trunk = await service.update_trunk(tenant_id, trunk_id, body)
        # Build gateway name for killgw
        from sqlalchemy import select as sa_select

        from new_phone.db.engine import AdminSessionLocal
        from new_phone.models.tenant import Tenant
        async with AdminSessionLocal() as s:
            t = (await s.execute(sa_select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
            if t and old_trunk:
                gw_name = f"{t.slug}-{old_trunk.name.lower().replace(' ', '-')}"
                await _sync_gateway_change(gw_name)
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
        # Get trunk name for gateway kill
        trunk = await service.get_trunk(tenant_id, trunk_id)
        result = await service.deactivate_trunk(tenant_id, trunk_id)
        if trunk:
            from sqlalchemy import select as sa_select

            from new_phone.db.engine import AdminSessionLocal
            from new_phone.models.tenant import Tenant
            async with AdminSessionLocal() as s:
                t = (await s.execute(sa_select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
                if t:
                    gw_name = f"{t.slug}-{trunk.name.lower().replace(' ', '-')}"
                    await _sync_gateway_change(gw_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
