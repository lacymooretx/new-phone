import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.ring_group import (
    RingGroupCreate,
    RingGroupResponse,
    RingGroupUpdate,
)
from new_phone.services.ring_group_service import RingGroupService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/ring-groups", tags=["ring-groups"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _group_to_response(group) -> dict:
    """Convert RingGroup ORM object to response dict with member_extension_ids."""
    data = {
        "id": group.id,
        "tenant_id": group.tenant_id,
        "group_number": group.group_number,
        "name": group.name,
        "ring_strategy": group.ring_strategy,
        "ring_time": group.ring_time,
        "ring_time_per_member": group.ring_time_per_member,
        "skip_busy": group.skip_busy,
        "cid_passthrough": group.cid_passthrough,
        "confirm_calls": group.confirm_calls,
        "failover_dest_type": group.failover_dest_type,
        "failover_dest_id": group.failover_dest_id,
        "member_extension_ids": [m.extension_id for m in group.members],
        "is_active": group.is_active,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }
    return data


@router.get("", response_model=list[RingGroupResponse])
async def list_ring_groups(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RING_GROUPS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RingGroupService(db)
    groups = await service.list_ring_groups(tenant_id)
    return [_group_to_response(g) for g in groups]


@router.post("", response_model=RingGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_ring_group(
    tenant_id: uuid.UUID,
    body: RingGroupCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_RING_GROUPS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RingGroupService(db)
    try:
        group = await service.create_ring_group(tenant_id, body)
        await _sync_dialplan()
        return _group_to_response(group)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{group_id}", response_model=RingGroupResponse)
async def get_ring_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RING_GROUPS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RingGroupService(db)
    group = await service.get_ring_group(tenant_id, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ring group not found")
    return _group_to_response(group)


@router.patch("/{group_id}", response_model=RingGroupResponse)
async def update_ring_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    body: RingGroupUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_RING_GROUPS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RingGroupService(db)
    try:
        group = await service.update_ring_group(tenant_id, group_id, body)
        await _sync_dialplan()
        return _group_to_response(group)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{group_id}", response_model=RingGroupResponse)
async def deactivate_ring_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_RING_GROUPS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RingGroupService(db)
    try:
        group = await service.deactivate_ring_group(tenant_id, group_id)
        await _sync_dialplan()
        return _group_to_response(group)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
