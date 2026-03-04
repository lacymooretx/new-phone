"""Zendesk integration API router."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.integrations.zendesk.client import ZendeskClient
from new_phone.integrations.zendesk.models import ZendeskConfig
from new_phone.integrations.zendesk.schemas import (
    ZendeskConfigCreate,
    ZendeskConfigResponse,
    ZendeskConfigUpdate,
    ZendeskTestResponse,
)
from new_phone.models.user import User
from new_phone.services.audit_utils import log_audit

logger = structlog.get_logger()

router = APIRouter(
    prefix="/tenants/{tenant_id}/integrations/zendesk",
    tags=["zendesk"],
)


# -- Helpers -----------------------------------------------------------------


async def _get_config(db: AsyncSession, tenant_id: uuid.UUID) -> ZendeskConfig | None:
    result = await db.execute(
        select(ZendeskConfig).where(ZendeskConfig.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _build_client(config: ZendeskConfig) -> ZendeskClient:
    return ZendeskClient(
        subdomain=config.subdomain,
        agent_email=config.agent_email,
        api_token=decrypt_value(config.encrypted_api_token),
    )


# -- Config CRUD -------------------------------------------------------------


@router.get("", response_model=ZendeskConfigResponse)
async def get_zendesk_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get Zendesk configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zendesk not configured")
    return ZendeskConfigResponse.model_validate(config)


@router.post("", response_model=ZendeskConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_zendesk_config(
    tenant_id: uuid.UUID,
    body: ZendeskConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create Zendesk configuration for the tenant."""
    existing = await _get_config(db, tenant_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zendesk already configured")

    config = ZendeskConfig(
        tenant_id=tenant_id,
        subdomain=body.subdomain,
        encrypted_api_token=encrypt_value(body.api_token),
        agent_email=body.agent_email,
        auto_ticket_on_missed=body.auto_ticket_on_missed,
        auto_ticket_on_voicemail=body.auto_ticket_on_voicemail,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "create", "zendesk_config", config.id)
    return ZendeskConfigResponse.model_validate(config)


@router.patch("", response_model=ZendeskConfigResponse)
async def update_zendesk_config(
    tenant_id: uuid.UUID,
    body: ZendeskConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update Zendesk configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zendesk not configured")

    update_data = body.model_dump(exclude_unset=True)

    # Encrypt token if provided
    api_token = update_data.pop("api_token", None)
    if api_token:
        config.encrypted_api_token = encrypt_value(api_token)

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "update", "zendesk_config", config.id)
    return ZendeskConfigResponse.model_validate(config)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zendesk_config(
    tenant_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete Zendesk configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zendesk not configured")
    config_id = config.id
    await db.delete(config)
    await db.commit()
    await log_audit(db, user, request, "delete", "zendesk_config", config_id)


@router.post("/test", response_model=ZendeskTestResponse)
async def test_zendesk_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Test Zendesk API connectivity."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zendesk not configured")
    client = _build_client(config)
    result = await client.test_connection()
    return ZendeskTestResponse(**result)
