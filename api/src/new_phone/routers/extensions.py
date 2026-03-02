import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.extension import Extension
from new_phone.models.user import User
from new_phone.schemas.calls import ExtensionLookupResponse
from new_phone.schemas.extension import (
    ExtensionCreate,
    ExtensionResponse,
    ExtensionUpdate,
    SIPPasswordResetResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.extension_service import ExtensionService

logger = structlog.get_logger()


async def _sync_directory() -> None:
    """Best-effort: notify FreeSWITCH of directory changes."""
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_directory_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/extensions", tags=["extensions"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[ExtensionResponse])
async def list_extensions(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    return await service.list_extensions(tenant_id, site_id=site_id)


@router.get("/lookup", response_model=ExtensionLookupResponse)
async def lookup_extension_by_number(
    tenant_id: uuid.UUID,
    number: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Look up an extension by number for click-to-call badge display."""
    _check_tenant_access(user, tenant_id)
    result = await db.execute(
        select(Extension).where(
            Extension.tenant_id == tenant_id,
            Extension.is_active.is_(True),
            or_(
                Extension.extension_number == number,
                Extension.internal_cid_number == number,
                Extension.external_cid_number == number,
            ),
        )
    )
    ext = result.scalar_one_or_none()
    if not ext:
        return ExtensionLookupResponse(is_internal=False)
    return ExtensionLookupResponse(
        extension_id=ext.id,
        extension_number=ext.extension_number,
        display_name=ext.internal_cid_name or ext.extension_number,
        dnd_enabled=ext.dnd_enabled,
        agent_status=ext.agent_status,
        is_internal=True,
    )


@router.post("", response_model=ExtensionResponse, status_code=status.HTTP_201_CREATED)
async def create_extension(
    tenant_id: uuid.UUID,
    body: ExtensionCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    try:
        ext = await service.create_extension(tenant_id, body)
        await log_audit(db, user, request, "create", "extension", ext.id)
        await _sync_directory()
        return ext
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{ext_id}", response_model=ExtensionResponse)
async def get_extension(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    ext = await service.get_extension(tenant_id, ext_id)
    if not ext:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found")
    return ext


@router.patch("/{ext_id}", response_model=ExtensionResponse)
async def update_extension(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    body: ExtensionUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    try:
        ext = await service.update_extension(tenant_id, ext_id, body)
        await log_audit(db, user, request, "update", "extension", ext.id)
        await _sync_directory()
        return ext
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{ext_id}", response_model=ExtensionResponse)
async def deactivate_extension(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    try:
        ext = await service.deactivate_extension(tenant_id, ext_id)
        await log_audit(db, user, request, "delete", "extension", ext.id)
        await _sync_directory()
        return ext
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/{ext_id}/reset-sip-password", response_model=SIPPasswordResetResponse)
async def reset_sip_password(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ExtensionService(db)
    try:
        new_password = await service.reset_sip_password(tenant_id, ext_id)
        await _sync_directory()
        return SIPPasswordResetResponse(sip_password=new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
