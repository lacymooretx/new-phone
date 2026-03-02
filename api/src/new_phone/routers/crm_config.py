"""CRM configuration router — config CRUD, test, cache invalidation."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.crm import (
    CRMCacheInvalidateRequest,
    CRMCacheInvalidateResponse,
    CRMConfigCreate,
    CRMConfigResponse,
    CRMConfigUpdate,
    CRMTestResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.crm_config_service import CRMConfigService

logger = structlog.get_logger()

router = APIRouter(prefix="/crm", tags=["crm"])


def _get_redis():
    from new_phone.main import redis_client

    return redis_client


@router.get("/config", response_model=CRMConfigResponse)
async def get_crm_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get CRM configuration for the current tenant."""
    service = CRMConfigService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CRM not configured")
    return CRMConfigResponse.model_validate(config)


@router.post("/config", response_model=CRMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_crm_config(
    body: CRMConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create CRM configuration for the current tenant."""
    service = CRMConfigService(db, redis=_get_redis())
    try:
        config = await service.create_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "crm_config", config.id)
    return CRMConfigResponse.model_validate(config)


@router.patch("/config", response_model=CRMConfigResponse)
async def update_crm_config(
    body: CRMConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update CRM configuration for the current tenant."""
    service = CRMConfigService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CRM not configured")
    try:
        updated = await service.update_config(config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "crm_config", updated.id)
    return CRMConfigResponse.model_validate(updated)


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crm_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete CRM configuration for the current tenant."""
    service = CRMConfigService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CRM not configured")
    await service.delete_config(config.id)
    await log_audit(db, user, request, "delete", "crm_config", config.id)


@router.post("/config/test", response_model=CRMTestResponse)
async def test_crm_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Test CRM API connectivity."""
    service = CRMConfigService(db, redis=_get_redis())
    try:
        result = await service.test_connection(user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    return CRMTestResponse(**result)


@router.post("/cache/invalidate", response_model=CRMCacheInvalidateResponse)
async def invalidate_crm_cache(
    body: CRMCacheInvalidateRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Invalidate CRM lookup cache for the current tenant."""
    service = CRMConfigService(db, redis=_get_redis())
    keys_deleted = await service.invalidate_cache(user.tenant_id, body.phone_number)
    return CRMCacheInvalidateResponse(keys_deleted=keys_deleted)
