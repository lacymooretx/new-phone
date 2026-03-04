"""Microsoft Teams integration router."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.integrations.teams.schemas import (
    TeamsConfigCreate,
    TeamsConfigResponse,
    TeamsConfigUpdate,
    TeamsPresenceMappingCreate,
    TeamsPresenceMappingResponse,
    TeamsPresenceSyncResponse,
)
from new_phone.integrations.teams.service import TeamsService
from new_phone.models.user import User
from new_phone.services.audit_utils import log_audit

logger = structlog.get_logger()

router = APIRouter(prefix="/integrations/teams", tags=["teams"])


# -- Config CRUD ---------------------------------------------------------------


@router.get("/config", response_model=TeamsConfigResponse)
async def get_teams_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get Teams configuration for the current tenant."""
    service = TeamsService(db)
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teams not configured"
        )
    return TeamsConfigResponse.model_validate(config)


@router.post(
    "/config", response_model=TeamsConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_teams_config(
    body: TeamsConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create Teams configuration for the current tenant."""
    service = TeamsService(db)
    try:
        config = await service.create_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from None
    await log_audit(db, user, request, "create", "teams_config", config.id)
    return TeamsConfigResponse.model_validate(config)


@router.patch("/config", response_model=TeamsConfigResponse)
async def update_teams_config(
    body: TeamsConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update Teams configuration for the current tenant."""
    service = TeamsService(db)
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teams not configured"
        )
    try:
        updated = await service.update_config(config.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
    await log_audit(db, user, request, "update", "teams_config", updated.id)
    return TeamsConfigResponse.model_validate(updated)


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teams_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete Teams configuration for the current tenant."""
    service = TeamsService(db)
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teams not configured"
        )
    await service.delete_config(config.id)
    await log_audit(db, user, request, "delete", "teams_config", config.id)


# -- Presence Mappings ---------------------------------------------------------


@router.get("/presence-mappings", response_model=list[TeamsPresenceMappingResponse])
async def list_presence_mappings(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List presence mappings for the current tenant."""
    service = TeamsService(db)
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teams not configured"
        )
    mappings = await service.list_presence_mappings(user.tenant_id)
    return [TeamsPresenceMappingResponse.model_validate(m) for m in mappings]


@router.post(
    "/presence-mappings",
    response_model=TeamsPresenceMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_presence_mapping(
    body: TeamsPresenceMappingCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create a presence mapping between a PBX extension and a Teams user."""
    service = TeamsService(db)
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teams not configured"
        )
    try:
        mapping = await service.create_presence_mapping(user.tenant_id, body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from None
    await log_audit(db, user, request, "create", "teams_presence_mapping", mapping.id)
    return TeamsPresenceMappingResponse.model_validate(mapping)


@router.delete(
    "/presence-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_presence_mapping(
    mapping_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete a presence mapping."""
    import uuid as _uuid

    service = TeamsService(db)
    try:
        await service.delete_presence_mapping(_uuid.UUID(mapping_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
    await log_audit(db, user, request, "delete", "teams_presence_mapping")


# -- Presence Sync -------------------------------------------------------------


@router.post("/presence/sync", response_model=TeamsPresenceSyncResponse)
async def sync_presence(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Trigger a presence sync between PBX and Teams (stub)."""
    service = TeamsService(db)
    try:
        result = await service.sync_presence(user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
    return TeamsPresenceSyncResponse(**result)
