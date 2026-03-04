"""Slack integration API router."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.integrations.slack.client import SlackClient
from new_phone.integrations.slack.models import SlackConfig
from new_phone.integrations.slack.schemas import (
    SlackConfigCreate,
    SlackConfigResponse,
    SlackConfigUpdate,
    SlackTestResponse,
)
from new_phone.models.user import User
from new_phone.services.audit_utils import log_audit

logger = structlog.get_logger()

router = APIRouter(
    prefix="/tenants/{tenant_id}/integrations/slack",
    tags=["slack"],
)


# -- Helpers -----------------------------------------------------------------


async def _get_config(db: AsyncSession, tenant_id: uuid.UUID) -> SlackConfig | None:
    result = await db.execute(
        select(SlackConfig).where(SlackConfig.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _build_client(config: SlackConfig) -> SlackClient:
    return SlackClient(
        bot_token=decrypt_value(config.encrypted_bot_token),
    )


# -- Config CRUD -------------------------------------------------------------


@router.get("", response_model=SlackConfigResponse)
async def get_slack_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get Slack configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack not configured")
    return SlackConfigResponse.model_validate(config)


@router.post("", response_model=SlackConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_slack_config(
    tenant_id: uuid.UUID,
    body: SlackConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create Slack configuration for the tenant."""
    existing = await _get_config(db, tenant_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slack already configured")

    config = SlackConfig(
        tenant_id=tenant_id,
        encrypted_bot_token=encrypt_value(body.bot_token),
        default_channel_id=body.default_channel_id,
        notify_missed_calls=body.notify_missed_calls,
        notify_voicemails=body.notify_voicemails,
        notify_queue_alerts=body.notify_queue_alerts,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "create", "slack_config", config.id)
    return SlackConfigResponse.model_validate(config)


@router.patch("", response_model=SlackConfigResponse)
async def update_slack_config(
    tenant_id: uuid.UUID,
    body: SlackConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update Slack configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack not configured")

    update_data = body.model_dump(exclude_unset=True)

    # Encrypt token if provided
    bot_token = update_data.pop("bot_token", None)
    if bot_token:
        config.encrypted_bot_token = encrypt_value(bot_token)

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    await log_audit(db, user, request, "update", "slack_config", config.id)
    return SlackConfigResponse.model_validate(config)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slack_config(
    tenant_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete Slack configuration for the tenant."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack not configured")
    config_id = config.id
    await db.delete(config)
    await db.commit()
    await log_audit(db, user, request, "delete", "slack_config", config_id)


@router.post("/test", response_model=SlackTestResponse)
async def test_slack_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Test Slack API connectivity."""
    config = await _get_config(db, tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack not configured")
    client = _build_client(config)
    result = await client.test_connection()
    return SlackTestResponse(**result)
