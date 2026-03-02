import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.page_group import (
    PageGroupCreate,
    PageGroupResponse,
    PageGroupUpdate,
)
from new_phone.services.page_group_service import PageGroupService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/page-groups", tags=["page-groups"])


async def _sync_paging_change() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_paging_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[PageGroupResponse])
async def list_page_groups(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_PAGING))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = PageGroupService(db)
    return await service.list_groups(tenant_id, site_id=site_id)


@router.post("", response_model=PageGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_page_group(
    tenant_id: uuid.UUID,
    body: PageGroupCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PageGroupService(db)
    try:
        group = await service.create_group(tenant_id, body)
        await _sync_paging_change()
        return group
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{group_id}", response_model=PageGroupResponse)
async def get_page_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_PAGING))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PageGroupService(db)
    group = await service.get_group(tenant_id, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page group not found")
    return group


@router.patch("/{group_id}", response_model=PageGroupResponse)
async def update_page_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    body: PageGroupUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PageGroupService(db)
    try:
        group = await service.update_group(tenant_id, group_id, body)
        await _sync_paging_change()
        return group
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{group_id}", response_model=PageGroupResponse)
async def deactivate_page_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PAGING))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PageGroupService(db)
    try:
        group = await service.deactivate(tenant_id, group_id)
        await _sync_paging_change()
        return group
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
