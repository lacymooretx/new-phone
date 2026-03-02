import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, get_current_user, require_permission
from new_phone.models.user import User
from new_phone.schemas.user import UserCreate, UserResponse, UserUpdate
from new_phone.services.user_service import UserService

router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["users"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    """Verify user can access the target tenant."""
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[UserResponse])
async def list_users(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_USERS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List users in a tenant."""
    _check_tenant_access(user, tenant_id)
    service = UserService(db)
    return await service.list_users(tenant_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    tenant_id: uuid.UUID,
    body: UserCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_USERS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create a user in a tenant."""
    _check_tenant_access(user, tenant_id)
    service = UserService(db)
    try:
        return await service.create_user(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get a specific user."""
    # Users can view themselves; managers+ can view anyone in tenant
    if user.id != user_id:
        _check_tenant_access(user, tenant_id)
        if not is_msp_role(user.role) and user.role not in ("tenant_admin", "tenant_manager"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = UserService(db)
    target = await service.get_user(tenant_id, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update a user."""
    # Users can update themselves (limited fields); managers+ can update anyone
    if user.id != user_id:
        _check_tenant_access(user, tenant_id)
        if not is_msp_role(user.role) and user.role not in ("tenant_admin", "tenant_manager"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = UserService(db)
    try:
        return await service.update_user(tenant_id, user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{user_id}", response_model=UserResponse)
async def deactivate_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_USERS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Deactivate a user."""
    _check_tenant_access(user, tenant_id)
    service = UserService(db)
    try:
        return await service.deactivate_user(tenant_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
