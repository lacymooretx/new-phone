import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.voicemail_message import (
    VMFolder,
    VoicemailForwardRequest,
    VoicemailMessageFilter,
    VoicemailMessagePlaybackResponse,
    VoicemailMessageResponse,
    VoicemailMessageSummaryResponse,
    VoicemailMessageUpdate,
)
from new_phone.services.voicemail_message_service import VoicemailMessageService

router = APIRouter(tags=["voicemail-messages"])


def _get_storage():
    from new_phone.main import storage_service
    return storage_service


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages",
    response_model=list[VoicemailMessageResponse],
)
async def list_messages(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    folder: VMFolder | None = None,
    is_read: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    _check_tenant_access(user, tenant_id)
    filters = VoicemailMessageFilter(
        folder=folder, is_read=is_read,
        date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    service = VoicemailMessageService(db, _get_storage())
    return await service.list_messages(tenant_id, box_id, filters)


@router.get(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages/{message_id}",
    response_model=VoicemailMessageResponse,
)
async def get_message(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    message_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    msg = await service.get_message(tenant_id, box_id, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg


@router.get(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages/{message_id}/playback",
    response_model=VoicemailMessagePlaybackResponse,
)
async def get_playback_url(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    message_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    url = await service.get_playback_url(tenant_id, box_id, message_id)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found or no file")
    return VoicemailMessagePlaybackResponse(url=url)


@router.patch(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages/{message_id}",
    response_model=VoicemailMessageResponse,
)
async def update_message(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    message_id: uuid.UUID,
    body: VoicemailMessageUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    msg = await service.update_message(tenant_id, box_id, message_id, body)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg


@router.delete(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages/{message_id}",
    response_model=VoicemailMessageResponse,
)
async def delete_message(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    message_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    msg = await service.soft_delete(tenant_id, box_id, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg


@router.post(
    "/tenants/{tenant_id}/voicemail-boxes/{box_id}/messages/{message_id}/forward",
    response_model=VoicemailMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def forward_message(
    tenant_id: uuid.UUID,
    box_id: uuid.UUID,
    message_id: uuid.UUID,
    body: VoicemailForwardRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    try:
        msg = await service.forward_message(tenant_id, box_id, message_id, body.target_box_id)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source message not found")
        return msg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get(
    "/tenants/{tenant_id}/voicemail-messages/unread-counts",
    response_model=list[VoicemailMessageSummaryResponse],
)
async def get_unread_counts(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_VOICEMAIL_MESSAGES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = VoicemailMessageService(db, _get_storage())
    return await service.get_unread_counts(tenant_id)
