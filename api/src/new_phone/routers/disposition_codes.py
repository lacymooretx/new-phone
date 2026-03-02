import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.disposition import (
    DispositionCodeCreate,
    DispositionCodeListCreate,
    DispositionCodeListResponse,
    DispositionCodeListUpdate,
    DispositionCodeResponse,
    DispositionCodeUpdate,
)
from new_phone.services.disposition_service import DispositionService

router = APIRouter(
    prefix="/tenants/{tenant_id}/disposition-code-lists",
    tags=["disposition-codes"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Code Lists ──


@router.get("", response_model=list[DispositionCodeListResponse])
async def list_code_lists(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    return await service.list_code_lists(tenant_id)


@router.post("", response_model=DispositionCodeListResponse, status_code=status.HTTP_201_CREATED)
async def create_code_list(
    tenant_id: uuid.UUID,
    body: DispositionCodeListCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    return await service.create_code_list(tenant_id, body)


@router.get("/{list_id}", response_model=DispositionCodeListResponse)
async def get_code_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    code_list = await service.get_code_list(tenant_id, list_id)
    if not code_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disposition code list not found")
    return code_list


@router.patch("/{list_id}", response_model=DispositionCodeListResponse)
async def update_code_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    body: DispositionCodeListUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    try:
        return await service.update_code_list(tenant_id, list_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{list_id}", response_model=DispositionCodeListResponse)
async def deactivate_code_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    try:
        return await service.deactivate_code_list(tenant_id, list_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Codes (nested under list) ──


@router.post("/{list_id}/codes", response_model=DispositionCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_code(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    body: DispositionCodeCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    try:
        return await service.create_code(tenant_id, list_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.patch("/{list_id}/codes/{code_id}", response_model=DispositionCodeResponse)
async def update_code(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    code_id: uuid.UUID,
    body: DispositionCodeUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    try:
        return await service.update_code(tenant_id, code_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{list_id}/codes/{code_id}", response_model=DispositionCodeResponse)
async def deactivate_code(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    code_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DispositionService(db)
    try:
        return await service.deactivate_code(tenant_id, code_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
