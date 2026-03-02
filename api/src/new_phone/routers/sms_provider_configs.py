import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.sms import (
    SMSProviderConfigCreate,
    SMSProviderConfigResponse,
    SMSProviderConfigUpdate,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.sms_provider_config_service import SMSProviderConfigService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/sms/providers", tags=["sms-providers"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[SMSProviderConfigResponse])
async def list_provider_configs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSProviderConfigService(db)
    configs = await service.list_configs(tenant_id)
    return [SMSProviderConfigResponse.model_validate(c) for c in configs]


@router.post("", response_model=SMSProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_config(
    tenant_id: uuid.UUID,
    body: SMSProviderConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSProviderConfigService(db)
    config = await service.create_config(tenant_id, body)
    await log_audit(db, user, request, "create", "sms_provider_config", config.id)
    return SMSProviderConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=SMSProviderConfigResponse)
async def get_provider_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSProviderConfigService(db)
    config = await service.get_config(tenant_id, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMS provider config not found")
    return SMSProviderConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=SMSProviderConfigResponse)
async def update_provider_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    body: SMSProviderConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSProviderConfigService(db)
    try:
        config = await service.update_config(tenant_id, config_id, body)
        await log_audit(db, user, request, "update", "sms_provider_config", config.id)
        return SMSProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{config_id}", response_model=SMSProviderConfigResponse)
async def delete_provider_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSProviderConfigService(db)
    try:
        config = await service.delete_config(tenant_id, config_id)
        await log_audit(db, user, request, "delete", "sms_provider_config", config.id)
        return SMSProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
