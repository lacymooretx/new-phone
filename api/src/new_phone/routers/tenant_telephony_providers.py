"""Tenant-level telephony provider configuration endpoints.

Prefix: /api/v1/tenants/{tenant_id}/telephony-providers
Permission: MANAGE_TRUNKS (tenant admin+)
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.telephony_provider_config import (
    TelephonyProviderConfigCreate,
    TelephonyProviderConfigResponse,
    TelephonyProviderConfigUpdate,
    TelephonyProviderEffective,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.telephony_provider_config_service import (
    TelephonyProviderConfigService,
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/tenants/{tenant_id}/telephony-providers",
    tags=["tenant-telephony-providers"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


@router.get("", response_model=list[TelephonyProviderConfigResponse])
async def list_tenant_configs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    configs = await service.list_configs(tenant_id)
    return [TelephonyProviderConfigResponse.model_validate(c) for c in configs]


@router.get("/effective", response_model=list[TelephonyProviderEffective])
async def get_effective_providers(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    results = await service.get_effective_providers(tenant_id)
    return [TelephonyProviderEffective(**r) for r in results]


@router.post(
    "",
    response_model=TelephonyProviderConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_config(
    tenant_id: uuid.UUID,
    body: TelephonyProviderConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    config = await service.create_config(body, tenant_id)
    await log_audit(
        db, user, request, "create", "telephony_provider_config", config.id
    )
    return TelephonyProviderConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def get_tenant_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    config = await service.get_config(config_id, tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony provider config not found",
        )
    return TelephonyProviderConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def update_tenant_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    body: TelephonyProviderConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    try:
        config = await service.update_config(config_id, body, tenant_id)
        await log_audit(
            db, user, request, "update", "telephony_provider_config", config.id
        )
        return TelephonyProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.delete("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def delete_tenant_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TRUNKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TelephonyProviderConfigService(db)
    try:
        config = await service.delete_config(config_id, tenant_id)
        await log_audit(
            db, user, request, "delete", "telephony_provider_config", config.id
        )
        return TelephonyProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
