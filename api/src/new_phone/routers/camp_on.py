"""Camp-On / Automatic Callback router — config CRUD and request management."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.camp_on import (
    CampOnCancelResponse,
    CampOnConfigCreate,
    CampOnConfigResponse,
    CampOnConfigUpdate,
    CampOnRequestResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.camp_on_service import CampOnService

logger = structlog.get_logger()

router = APIRouter(prefix="/camp-on", tags=["camp-on"])


def _get_redis():
    from new_phone.main import redis_client

    return redis_client


# ── Config CRUD ──


@router.get("/config", response_model=CampOnConfigResponse)
async def get_camp_on_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = CampOnService(db, _get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp-on not configured")
    return config


@router.post("/config", response_model=CampOnConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_camp_on_config(
    body: CampOnConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = CampOnService(db, _get_redis())
    try:
        config = await service.create_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "camp_on_config", config.id)
    return config


@router.patch("/config", response_model=CampOnConfigResponse)
async def update_camp_on_config(
    body: CampOnConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = CampOnService(db, _get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp-on not configured")
    try:
        updated = await service.update_config(config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "camp_on_config", updated.id)
    return updated


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camp_on_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = CampOnService(db, _get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp-on not configured")
    await service.delete_config(config.id)
    await log_audit(db, user, request, "delete", "camp_on_config", config.id)


# ── Request list/get/cancel ──


@router.get("/requests", response_model=list[CampOnRequestResponse])
async def list_camp_on_requests(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    status_filter: str | None = Query(None, alias="status"),
    target_ext: str | None = Query(None),
):
    service = CampOnService(db, _get_redis())
    return await service.list_requests(user.tenant_id, status_filter, target_ext)


@router.get("/requests/{request_id}", response_model=CampOnRequestResponse)
async def get_camp_on_request(
    request_id: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid

    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request ID"
        ) from None

    service = CampOnService(db, _get_redis())
    req = await service.get_request(user.tenant_id, rid)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camp-on request not found"
        )
    return req


@router.delete("/requests/{request_id}", response_model=CampOnCancelResponse)
async def cancel_camp_on_request(
    request_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid

    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request ID"
        ) from None

    service = CampOnService(db, _get_redis())
    try:
        req = await service.cancel_request(user.tenant_id, rid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "cancel", "camp_on_request", rid)
    return CampOnCancelResponse(status=req.status)
