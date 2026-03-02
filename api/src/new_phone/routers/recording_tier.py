"""Recording storage tiering router — config CRUD, retrieval, legal hold, stats."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.recording_tier import (
    RecordingLegalHoldRequest,
    RecordingLegalHoldResponse,
    RecordingRetrievalResponse,
    RecordingStorageStats,
    RecordingTierConfigCreate,
    RecordingTierConfigResponse,
    RecordingTierConfigUpdate,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.recording_tier_service import RecordingTierService

logger = structlog.get_logger()

router = APIRouter(prefix="/recording-tier", tags=["recording-tier"])


def _get_storage():
    from new_phone.main import storage_service

    return storage_service


# ── Config CRUD ──


@router.get("/config", response_model=RecordingTierConfigResponse)
async def get_tier_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tiering not configured")
    return config


@router.post(
    "/config", response_model=RecordingTierConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_tier_config(
    body: RecordingTierConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    try:
        config = await service.create_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "recording_tier_config", config.id)
    return config


@router.patch("/config", response_model=RecordingTierConfigResponse)
async def update_tier_config(
    body: RecordingTierConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tiering not configured")
    try:
        updated = await service.update_config(config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "recording_tier_config", updated.id)
    return updated


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tier_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tiering not configured")
    await service.delete_config(config.id)
    await log_audit(db, user, request, "delete", "recording_tier_config", config.id)


# ── Retrieval ──


@router.post("/retrieve/{recording_id}", response_model=RecordingRetrievalResponse)
async def request_retrieval(
    recording_id: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid

    try:
        rid = _uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recording ID"
        ) from None

    service = RecordingTierService(db, _get_storage())
    recording = await service.request_retrieval(user.tenant_id, rid)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found or retrieval failed"
        )

    if recording.storage_tier == "hot" and not recording.retrieval_expires_at:
        return RecordingRetrievalResponse(
            recording_id=rid,
            status="already_hot",
            message="Recording is already in hot storage",
        )

    return RecordingRetrievalResponse(
        recording_id=rid,
        status="retrieved",
        message=f"Recording retrieved to hot storage, expires {recording.retrieval_expires_at.isoformat()}",
    )


# ── Legal hold ──


@router.post("/legal-hold", response_model=RecordingLegalHoldResponse)
async def set_legal_hold(
    body: RecordingLegalHoldRequest,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_RECORDINGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    count = await service.set_legal_hold(user.tenant_id, body.recording_ids, body.hold, user.id)
    action = "set_legal_hold" if body.hold else "remove_legal_hold"
    await log_audit(db, user, request, action, "recordings", changes={"count": count})
    return RecordingLegalHoldResponse(updated_count=count)


# ── Storage stats ──


@router.get("/stats", response_model=RecordingStorageStats)
async def get_storage_stats(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = RecordingTierService(db, _get_storage())
    return await service.get_storage_stats(user.tenant_id)
