import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.ivr_menu import (
    IVRMenuCreate,
    IVRMenuResponse,
    IVRMenuUpdate,
)
from new_phone.services.ivr_menu_service import IVRMenuService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/ivr-menus", tags=["ivr-menus"])


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[IVRMenuResponse])
async def list_ivr_menus(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = IVRMenuService(db)
    return await service.list_menus(tenant_id)


@router.post("", response_model=IVRMenuResponse, status_code=status.HTTP_201_CREATED)
async def create_ivr_menu(
    tenant_id: uuid.UUID,
    body: IVRMenuCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = IVRMenuService(db)
    try:
        menu = await service.create_menu(tenant_id, body)
        await _sync_dialplan()
        return menu
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{menu_id}", response_model=IVRMenuResponse)
async def get_ivr_menu(
    tenant_id: uuid.UUID,
    menu_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = IVRMenuService(db)
    menu = await service.get_menu(tenant_id, menu_id)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IVR menu not found")
    return menu


@router.patch("/{menu_id}", response_model=IVRMenuResponse)
async def update_ivr_menu(
    tenant_id: uuid.UUID,
    menu_id: uuid.UUID,
    body: IVRMenuUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = IVRMenuService(db)
    try:
        menu = await service.update_menu(tenant_id, menu_id, body)
        await _sync_dialplan()
        return menu
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{menu_id}", response_model=IVRMenuResponse)
async def deactivate_ivr_menu(
    tenant_id: uuid.UUID,
    menu_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = IVRMenuService(db)
    try:
        menu = await service.deactivate(tenant_id, menu_id)
        await _sync_dialplan()
        return menu
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
