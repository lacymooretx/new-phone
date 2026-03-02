import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.did import DIDCreate, DIDResponse, DIDUpdate
from new_phone.services.did_service import DIDService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/dids", tags=["dids"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[DIDResponse])
async def list_dids(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = DIDService(db)
    return await service.list_dids(tenant_id, site_id=site_id)


@router.post("", response_model=DIDResponse, status_code=status.HTTP_201_CREATED)
async def create_did(
    tenant_id: uuid.UUID,
    body: DIDCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DIDService(db)
    try:
        did = await service.create_did(tenant_id, body)
        await _sync_dialplan()
        return did
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{did_id}", response_model=DIDResponse)
async def get_did(
    tenant_id: uuid.UUID,
    did_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DIDService(db)
    did = await service.get_did(tenant_id, did_id)
    if not did:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DID not found")
    return did


@router.patch("/{did_id}", response_model=DIDResponse)
async def update_did(
    tenant_id: uuid.UUID,
    did_id: uuid.UUID,
    body: DIDUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DIDService(db)
    try:
        did = await service.update_did(tenant_id, did_id, body)
        await _sync_dialplan()
        return did
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{did_id}", response_model=DIDResponse)
async def deactivate_did(
    tenant_id: uuid.UUID,
    did_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DIDService(db)
    try:
        did = await service.deactivate_did(tenant_id, did_id)
        await _sync_dialplan()
        return did
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
