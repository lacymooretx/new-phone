from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.sso import (
    SSOProviderCreate,
    SSOProviderResponse,
    SSOProviderUpdate,
    SSORoleMappingCreate,
    SSORoleMappingResponse,
    SSOTestResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.sso_config_service import SSOConfigService

logger = structlog.get_logger()

router = APIRouter(prefix="/sso-config", tags=["sso"])


@router.get("", response_model=SSOProviderResponse)
async def get_sso_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get SSO provider configuration for the current user's tenant."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    return SSOProviderResponse.model_validate(provider)


@router.post("", response_model=SSOProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_sso_config(
    body: SSOProviderCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create SSO provider configuration for the current user's tenant."""
    service = SSOConfigService(db)
    try:
        provider = await service.create_provider(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "sso_provider", provider.id)
    return SSOProviderResponse.model_validate(provider)


@router.patch("", response_model=SSOProviderResponse)
async def update_sso_config(
    body: SSOProviderUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update SSO provider configuration for the current user's tenant."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    try:
        updated = await service.update_provider(provider.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "sso_provider", updated.id)
    return SSOProviderResponse.model_validate(updated)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete SSO provider configuration for the current user's tenant."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    await service.delete_provider(provider.id)
    await log_audit(db, user, request, "delete", "sso_provider", provider.id)


@router.post("/test", response_model=SSOTestResponse)
async def test_sso_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Test SSO provider connectivity by fetching the OIDC discovery document."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    result = await service.test_connection(provider.id)
    return SSOTestResponse(**result)


# ── Role Mappings ──────────────────────────────────────────────────


@router.get("/role-mappings", response_model=list[SSORoleMappingResponse])
async def list_role_mappings(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List SSO group-to-role mappings for the current user's tenant."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    mappings = await service.list_role_mappings(provider.id)
    return [SSORoleMappingResponse.model_validate(m) for m in mappings]


@router.post("/role-mappings", response_model=SSORoleMappingResponse, status_code=status.HTTP_201_CREATED)
async def add_role_mapping(
    body: SSORoleMappingCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Add a group-to-role mapping."""
    service = SSOConfigService(db)
    provider = await service.get_provider(user.tenant_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    try:
        mapping = await service.add_role_mapping(
            provider.id, body.external_group_id, body.external_group_name, body.pbx_role
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "sso_role_mapping", mapping.id)
    return SSORoleMappingResponse.model_validate(mapping)


@router.delete("/role-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_mapping(
    mapping_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete a group-to-role mapping."""
    import uuid as _uuid
    service = SSOConfigService(db)
    try:
        await service.remove_role_mapping(_uuid.UUID(mapping_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "delete", "sso_role_mapping")
