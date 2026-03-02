import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.security_config import (
    PanicNotificationTargetCreate,
    PanicNotificationTargetResponse,
    SecurityConfigResponse,
    SecurityConfigUpdate,
)
from new_phone.services.security_config_service import SecurityConfigService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/security-config", tags=["security"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=SecurityConfigResponse)
async def get_security_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SecurityConfigService(db)
    config = await service.get_config(tenant_id)
    if not config:
        # Auto-create with defaults
        config = await service.create_or_update(tenant_id, SecurityConfigUpdate())
    return config


@router.put("", response_model=SecurityConfigResponse)
async def update_security_config(
    tenant_id: uuid.UUID,
    body: SecurityConfigUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SecurityConfigService(db)
    config = await service.create_or_update(tenant_id, body)
    await _sync_security_change()
    return config


@router.get("/notification-targets", response_model=list[PanicNotificationTargetResponse])
async def list_notification_targets(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SecurityConfigService(db)
    config = await service.get_config(tenant_id)
    if not config:
        return []
    return await service.list_notification_targets(tenant_id, config.id)


@router.post(
    "/notification-targets",
    response_model=PanicNotificationTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_notification_target(
    tenant_id: uuid.UUID,
    body: PanicNotificationTargetCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SecurityConfigService(db)
    config = await service.get_config(tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security config not found. Create it first.",
        )
    try:
        return await service.add_notification_target(tenant_id, config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.delete("/notification-targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_notification_target(
    tenant_id: uuid.UUID,
    target_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SecurityConfigService(db)
    try:
        await service.remove_notification_target(tenant_id, target_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


async def _sync_security_change() -> None:
    try:
        from new_phone.main import config_sync

        if config_sync and hasattr(config_sync, "notify_security_change"):
            await config_sync.notify_security_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))
