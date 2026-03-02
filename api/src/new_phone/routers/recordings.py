import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.recording import (
    RecordingFilter,
    RecordingPlaybackResponse,
    RecordingResponse,
)
from new_phone.services.recording_service import RecordingService

router = APIRouter(prefix="/tenants/{tenant_id}/recordings", tags=["recordings"])


def _get_storage():
    from new_phone.main import storage_service

    return storage_service


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    call_id: str | None = None,
    cdr_id: uuid.UUID | None = None,
    storage_tier: str | None = None,
    legal_hold: bool | None = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    _check_tenant_access(user, tenant_id)
    filters = RecordingFilter(
        date_from=date_from,
        date_to=date_to,
        call_id=call_id,
        cdr_id=cdr_id,
        storage_tier=storage_tier,
        legal_hold=legal_hold,
        limit=limit,
        offset=offset,
    )
    service = RecordingService(db, _get_storage())
    return await service.list_recordings(tenant_id, filters)


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    tenant_id: uuid.UUID,
    recording_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RecordingService(db, _get_storage())
    recording = await service.get_recording(tenant_id, recording_id)
    if not recording:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
    return recording


@router.get("/{recording_id}/playback", response_model=RecordingPlaybackResponse)
async def get_playback_url(
    tenant_id: uuid.UUID,
    recording_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RecordingService(db, _get_storage())
    result = await service.get_playback_url(tenant_id, recording_id)
    if result["status"] == "missing":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found or no file"
        )
    if result["status"] == "cold":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recording is archived in cold storage. Use POST /recording-tier/retrieve/{id} to request retrieval.",
        )
    return RecordingPlaybackResponse(url=result["url"])


@router.delete("/{recording_id}", response_model=RecordingResponse)
async def delete_recording(
    tenant_id: uuid.UUID,
    recording_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = RecordingService(db, _get_storage())
    recording = await service.soft_delete(tenant_id, recording_id)
    if not recording:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
    return recording
