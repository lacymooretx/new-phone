import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.paging_zone import PagingZoneCreate, PagingZoneResponse, PagingZoneUpdate
from new_phone.services.paging_zone_service import PagingZoneService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/paging-zones", tags=["security"])


async def _sync_paging_zone_change() -> None:
    try:
        from new_phone.main import config_sync

        if config_sync:
            await config_sync.notify_paging_zone_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[PagingZoneResponse])
async def list_paging_zones(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_PAGING_ZONES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    return await service.list_zones(tenant_id)


@router.post("", response_model=PagingZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_paging_zone(
    tenant_id: uuid.UUID,
    body: PagingZoneCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING_ZONES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    try:
        zone = await service.create_zone(tenant_id, body)
        await _sync_paging_zone_change()
        return zone
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{zone_id}", response_model=PagingZoneResponse)
async def get_paging_zone(
    tenant_id: uuid.UUID,
    zone_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_PAGING_ZONES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    zone = await service.get_zone(tenant_id, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paging zone not found")
    return zone


@router.patch("/{zone_id}", response_model=PagingZoneResponse)
async def update_paging_zone(
    tenant_id: uuid.UUID,
    zone_id: uuid.UUID,
    body: PagingZoneUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING_ZONES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    try:
        zone = await service.update_zone(tenant_id, zone_id, body)
        await _sync_paging_zone_change()
        return zone
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{zone_id}", response_model=PagingZoneResponse)
async def deactivate_paging_zone(
    tenant_id: uuid.UUID,
    zone_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING_ZONES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    try:
        zone = await service.deactivate_zone(tenant_id, zone_id)
        await _sync_paging_zone_change()
        return zone
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/emergency-allcall", response_model=list[PagingZoneResponse])
async def trigger_emergency_allcall(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.TRIGGER_PANIC))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PagingZoneService(db)
    return await service.trigger_emergency_allcall(tenant_id)
