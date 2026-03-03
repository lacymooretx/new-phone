"""MSP-level telephony provider configuration endpoints.

Prefix: /api/v1/platform/telephony-providers
Permission: MANAGE_PLATFORM (MSP super admin only)
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.telephony_provider_config import (
    TelephonyProviderConfigCreate,
    TelephonyProviderConfigResponse,
    TelephonyProviderConfigUpdate,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.telephony_provider_config_service import (
    TelephonyProviderConfigService,
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/platform/telephony-providers",
    tags=["platform-telephony-providers"],
)


@router.get("", response_model=list[TelephonyProviderConfigResponse])
async def list_platform_configs(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = TelephonyProviderConfigService(db)
    configs = await service.list_configs(tenant_id=None)
    return [TelephonyProviderConfigResponse.model_validate(c) for c in configs]


@router.post(
    "",
    response_model=TelephonyProviderConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_platform_config(
    body: TelephonyProviderConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = TelephonyProviderConfigService(db)
    config = await service.create_config(body, tenant_id=None)
    await log_audit(
        db, user, request, "create", "telephony_provider_config", config.id
    )
    return TelephonyProviderConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def get_platform_config(
    config_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = TelephonyProviderConfigService(db)
    config = await service.get_config(config_id, tenant_id=None)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony provider config not found",
        )
    return TelephonyProviderConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def update_platform_config(
    config_id: uuid.UUID,
    body: TelephonyProviderConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = TelephonyProviderConfigService(db)
    try:
        config = await service.update_config(config_id, body, tenant_id=None)
        await log_audit(
            db, user, request, "update", "telephony_provider_config", config.id
        )
        return TelephonyProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.delete("/{config_id}", response_model=TelephonyProviderConfigResponse)
async def delete_platform_config(
    config_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = TelephonyProviderConfigService(db)
    try:
        config = await service.delete_config(config_id, tenant_id=None)
        await log_audit(
            db, user, request, "delete", "telephony_provider_config", config.id
        )
        return TelephonyProviderConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
