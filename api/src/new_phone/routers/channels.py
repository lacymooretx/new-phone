import json
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.db.rls import set_tenant_context
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.channel_config import ChannelConfig
from new_phone.models.user import User
from new_phone.schemas.channel_config import (
    ChannelConfigCreate,
    ChannelConfigResponse,
    ChannelConfigUpdate,
)
from new_phone.services.audit_utils import log_audit

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/channels", tags=["channels"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[ChannelConfigResponse])
async def list_channel_configs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        select(ChannelConfig)
        .where(
            ChannelConfig.tenant_id == tenant_id,
            ChannelConfig.is_active.is_(True),
        )
        .order_by(ChannelConfig.display_name)
    )
    configs = list(result.scalars().all())
    return [ChannelConfigResponse.model_validate(c) for c in configs]


@router.post("", response_model=ChannelConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_channel_config(
    tenant_id: uuid.UUID,
    body: ChannelConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    await set_tenant_context(db, tenant_id)

    encrypted = encrypt_value(json.dumps(body.credentials))

    config = ChannelConfig(
        tenant_id=tenant_id,
        channel_type=body.channel_type,
        display_name=body.display_name,
        encrypted_credentials=encrypted,
        is_active=body.is_active,
        queue_id=body.queue_id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "create", "channel_config", config.id)
    return ChannelConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=ChannelConfigResponse)
async def get_channel_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        select(ChannelConfig).where(
            ChannelConfig.id == config_id,
            ChannelConfig.tenant_id == tenant_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")
    return ChannelConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=ChannelConfigResponse)
async def update_channel_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    body: ChannelConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        select(ChannelConfig).where(
            ChannelConfig.id == config_id,
            ChannelConfig.tenant_id == tenant_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")

    update_data = body.model_dump(exclude_unset=True)

    if "credentials" in update_data and update_data["credentials"] is not None:
        config.encrypted_credentials = encrypt_value(json.dumps(update_data.pop("credentials")))

    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "update", "channel_config", config.id)
    return ChannelConfigResponse.model_validate(config)


@router.delete("/{config_id}", response_model=ChannelConfigResponse)
async def delete_channel_config(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        select(ChannelConfig).where(
            ChannelConfig.id == config_id,
            ChannelConfig.tenant_id == tenant_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")

    config.is_active = False
    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "delete", "channel_config", config.id)
    return ChannelConfigResponse.model_validate(config)
