import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.building_webhook import (
    BuildingWebhookActionCreate,
    BuildingWebhookActionResponse,
    BuildingWebhookCreate,
    BuildingWebhookLogResponse,
    BuildingWebhookResponse,
    BuildingWebhookUpdate,
)
from new_phone.services.building_webhook_service import BuildingWebhookService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/building-webhooks", tags=["security"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[BuildingWebhookResponse])
async def list_building_webhooks(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    return await service.list_webhooks(tenant_id)


@router.post("", response_model=BuildingWebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_building_webhook(
    tenant_id: uuid.UUID,
    body: BuildingWebhookCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    return await service.create_webhook(tenant_id, body)


@router.get("/{webhook_id}", response_model=BuildingWebhookResponse)
async def get_building_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    webhook = await service.get_webhook(tenant_id, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Building webhook not found"
        )
    return webhook


@router.patch("/{webhook_id}", response_model=BuildingWebhookResponse)
async def update_building_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    body: BuildingWebhookUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    try:
        return await service.update_webhook(tenant_id, webhook_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{webhook_id}", response_model=BuildingWebhookResponse)
async def deactivate_building_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    try:
        return await service.deactivate_webhook(tenant_id, webhook_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post(
    "/{webhook_id}/actions",
    response_model=BuildingWebhookActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_webhook_action(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    body: BuildingWebhookActionCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    try:
        return await service.add_action(tenant_id, webhook_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.delete("/{webhook_id}/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_webhook_action(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    action_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    try:
        await service.remove_action(tenant_id, action_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/{webhook_id}/logs", response_model=list[BuildingWebhookLogResponse])
async def list_webhook_logs(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_BUILDING_WEBHOOKS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(50, ge=1, le=200),
):
    _check_tenant_access(user, tenant_id)
    service = BuildingWebhookService(db)
    return await service.list_logs(tenant_id, webhook_id, limit=limit)
