import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.time_condition import (
    TimeConditionCreate,
    TimeConditionResponse,
    TimeConditionUpdate,
)
from new_phone.services.time_condition_service import TimeConditionService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/time-conditions", tags=["time-conditions"])


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


@router.get("", response_model=list[TimeConditionResponse])
async def list_time_conditions(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = TimeConditionService(db)
    return await service.list_time_conditions(tenant_id, site_id=site_id)


@router.post("", response_model=TimeConditionResponse, status_code=status.HTTP_201_CREATED)
async def create_time_condition(
    tenant_id: uuid.UUID,
    body: TimeConditionCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TimeConditionService(db)
    try:
        tc = await service.create_time_condition(tenant_id, body)
        await _sync_dialplan()
        return tc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{tc_id}", response_model=TimeConditionResponse)
async def get_time_condition(
    tenant_id: uuid.UUID,
    tc_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TimeConditionService(db)
    tc = await service.get_time_condition(tenant_id, tc_id)
    if not tc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time condition not found")
    return tc


@router.patch("/{tc_id}", response_model=TimeConditionResponse)
async def update_time_condition(
    tenant_id: uuid.UUID,
    tc_id: uuid.UUID,
    body: TimeConditionUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TimeConditionService(db)
    try:
        tc = await service.update_time_condition(tenant_id, tc_id, body)
        await _sync_dialplan()
        return tc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{tc_id}", response_model=TimeConditionResponse)
async def deactivate_time_condition(
    tenant_id: uuid.UUID,
    tc_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TimeConditionService(db)
    try:
        tc = await service.deactivate(tenant_id, tc_id)
        await _sync_dialplan()
        return tc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
