import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.voicemail_box import (
    PinResetResponse,
    VoicemailBoxCreate,
    VoicemailBoxResponse,
    VoicemailBoxUpdate,
)
from new_phone.services.voicemail_service import VoicemailService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/voicemail-boxes", tags=["voicemail"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[VoicemailBoxResponse])
async def list_voicemail_boxes(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    return await service.list_voicemail_boxes(tenant_id)


@router.post("", response_model=VoicemailBoxResponse, status_code=status.HTTP_201_CREATED)
async def create_voicemail_box(
    tenant_id: uuid.UUID,
    body: VoicemailBoxCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    try:
        box = await service.create_voicemail_box(tenant_id, body)
        await _sync_dialplan()
        return box
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{box_id}", response_model=VoicemailBoxResponse)
async def get_voicemail_box(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    box = await service.get_voicemail_box(tenant_id, box_id)
    if not box:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voicemail box not found")
    return box


@router.patch("/{box_id}", response_model=VoicemailBoxResponse)
async def update_voicemail_box(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    body: VoicemailBoxUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    try:
        box = await service.update_voicemail_box(tenant_id, box_id, body)
        await _sync_dialplan()
        return box
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{box_id}", response_model=VoicemailBoxResponse)
async def deactivate_voicemail_box(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    try:
        box = await service.deactivate_voicemail_box(tenant_id, box_id)
        await _sync_dialplan()
        return box
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/{box_id}/reset-pin", response_model=PinResetResponse)
async def reset_pin(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailService(db)
    try:
        new_pin = await service.reset_pin(tenant_id, box_id)
        await _sync_dialplan()
        return PinResetResponse(pin=new_pin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
