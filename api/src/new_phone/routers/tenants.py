import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from new_phone.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_ALL_TENANTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List all tenants (MSP roles only)."""
    service = TenantService(db)
    return await service.list_tenants()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create a new tenant (MSP Super Admin only)."""
    service = TenantService(db)
    try:
        return await service.create_tenant(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get a specific tenant."""
    # Non-MSP users can only view their own tenant
    from new_phone.auth.rbac import is_msp_role

    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update a tenant."""
    from new_phone.auth.rbac import is_msp_role

    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = TenantService(db)
    try:
        return await service.update_tenant(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{tenant_id}", response_model=TenantResponse)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Deactivate a tenant (MSP Super Admin only)."""
    service = TenantService(db)
    try:
        return await service.deactivate_tenant(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
