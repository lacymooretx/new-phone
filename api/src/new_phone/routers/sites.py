import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.site import (
    SiteCreate,
    SiteResponse,
    SiteSummaryResponse,
    SiteUpdate,
)
from new_phone.services.site_service import SiteService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/sites", tags=["sites"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    return await service.list_sites(tenant_id)


@router.get("/summaries", response_model=list[SiteSummaryResponse])
async def list_site_summaries(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    return await service.list_sites(tenant_id)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    tenant_id: uuid.UUID,
    body: SiteCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    try:
        return await service.create_site(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    tenant_id: uuid.UUID,
    site_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    site = await service.get_site(tenant_id, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    tenant_id: uuid.UUID,
    site_id: uuid.UUID,
    body: SiteUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    try:
        return await service.update_site(tenant_id, site_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{site_id}", response_model=SiteResponse)
async def deactivate_site(
    tenant_id: uuid.UUID,
    site_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SiteService(db)
    try:
        return await service.deactivate(tenant_id, site_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
