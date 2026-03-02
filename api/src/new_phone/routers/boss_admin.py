import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.extension import Extension
from new_phone.models.user import User
from new_phone.schemas.boss_admin import (
    BossAdminCreate,
    BossAdminResponse,
    BossAdminUpdate,
)
from new_phone.services.boss_admin_service import BossAdminService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/tenants/{tenant_id}/boss-admin",
    tags=["boss-admin"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/relationships", response_model=list[BossAdminResponse])
async def list_relationships(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    executive_id: Annotated[uuid.UUID | None, Query()] = None,
    assistant_id: Annotated[uuid.UUID | None, Query()] = None,
):
    _check_tenant_access(user, tenant_id)
    service = BossAdminService(db)
    return await service.list_relationships(tenant_id, executive_id, assistant_id)


@router.post(
    "/relationships",
    response_model=BossAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    tenant_id: uuid.UUID,
    body: BossAdminCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BossAdminService(db)
    try:
        return await service.create_relationship(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/relationships/{rel_id}", response_model=BossAdminResponse)
async def get_relationship(
    tenant_id: uuid.UUID,
    rel_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BossAdminService(db)
    rel = await service.get_relationship(tenant_id, rel_id)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boss/admin relationship not found",
        )
    return rel


@router.patch("/relationships/{rel_id}", response_model=BossAdminResponse)
async def update_relationship(
    tenant_id: uuid.UUID,
    rel_id: uuid.UUID,
    body: BossAdminUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BossAdminService(db)
    try:
        return await service.update_relationship(tenant_id, rel_id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.delete(
    "/relationships/{rel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    tenant_id: uuid.UUID,
    rel_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BossAdminService(db)
    try:
        await service.delete_relationship(tenant_id, rel_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


async def _get_user_extension_id(db: AsyncSession, user: User) -> uuid.UUID | None:
    """Look up the extension assigned to this user."""
    result = await db.execute(
        select(Extension.id).where(
            Extension.user_id == user.id,
            Extension.tenant_id == user.tenant_id,
            Extension.is_active.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    return row


@router.get("/my-executives", response_model=list[BossAdminResponse])
async def get_my_executives(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get executives for the current user's extension (assistant view)."""
    _check_tenant_access(user, tenant_id)
    ext_id = await _get_user_extension_id(db, user)
    if not ext_id:
        return []
    service = BossAdminService(db)
    return await service.get_executives_for_assistant(tenant_id, ext_id)


@router.get("/my-assistants", response_model=list[BossAdminResponse])
async def get_my_assistants(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get assistants for the current user's extension (executive view)."""
    _check_tenant_access(user, tenant_id)
    ext_id = await _get_user_extension_id(db, user)
    if not ext_id:
        return []
    service = BossAdminService(db)
    return await service.get_assistants_for_executive(tenant_id, ext_id)
