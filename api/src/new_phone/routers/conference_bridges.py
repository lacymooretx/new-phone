import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.conference_bridge import (
    ConferenceBridgeCreate,
    ConferenceBridgeResponse,
    ConferenceBridgeUpdate,
)
from new_phone.services.conference_bridge_service import ConferenceBridgeService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/conference-bridges", tags=["conference-bridges"])


async def _sync_conference_change() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_conference_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[ConferenceBridgeResponse])
async def list_conference_bridges(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CONFERENCES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ConferenceBridgeService(db)
    return await service.list_bridges(tenant_id)


@router.post("", response_model=ConferenceBridgeResponse, status_code=status.HTTP_201_CREATED)
async def create_conference_bridge(
    tenant_id: uuid.UUID,
    body: ConferenceBridgeCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_CONFERENCES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ConferenceBridgeService(db)
    try:
        bridge = await service.create_bridge(tenant_id, body)
        await _sync_conference_change()
        return bridge
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{bridge_id}", response_model=ConferenceBridgeResponse)
async def get_conference_bridge(
    tenant_id: uuid.UUID,
    bridge_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CONFERENCES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ConferenceBridgeService(db)
    bridge = await service.get_bridge(tenant_id, bridge_id)
    if not bridge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference bridge not found")
    return bridge


@router.patch("/{bridge_id}", response_model=ConferenceBridgeResponse)
async def update_conference_bridge(
    tenant_id: uuid.UUID,
    bridge_id: uuid.UUID,
    body: ConferenceBridgeUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_CONFERENCES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ConferenceBridgeService(db)
    try:
        bridge = await service.update_bridge(tenant_id, bridge_id, body)
        await _sync_conference_change()
        return bridge
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{bridge_id}", response_model=ConferenceBridgeResponse)
async def deactivate_conference_bridge(
    tenant_id: uuid.UUID,
    bridge_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_CONFERENCES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ConferenceBridgeService(db)
    try:
        bridge = await service.deactivate(tenant_id, bridge_id)
        await _sync_conference_change()
        return bridge
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
