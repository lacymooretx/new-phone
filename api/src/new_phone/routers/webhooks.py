import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.schemas.webhook import (
    WebhookDeliveryLogResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
    WebhookTestRequest,
)
from new_phone.services.webhook_service import WebhookService

router = APIRouter(prefix="/tenants/{tenant_id}/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookSubscriptionResponse])
async def list_webhooks(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    return await service.list_subscriptions(tenant_id)


@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    tenant_id: uuid.UUID,
    data: WebhookSubscriptionCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    return await service.create_subscription(
        tenant_id,
        name=data.name,
        target_url=data.target_url,
        event_types=data.event_types,
        description=data.description,
        is_active=data.is_active,
    )


@router.get("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    sub = await service.get_subscription(tenant_id, webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return sub


@router.put("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    data: WebhookSubscriptionUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    sub = await service.update_subscription(tenant_id, webhook_id, **data.model_dump(exclude_unset=True))
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return sub


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    deleted = await service.delete_subscription(tenant_id, webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/{webhook_id}/deliveries", response_model=dict)
async def list_deliveries(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    service = WebhookService(db)
    logs, total = await service.list_delivery_logs(tenant_id, webhook_id, page, per_page)
    return {
        "items": [WebhookDeliveryLogResponse.model_validate(log) for log in logs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/{webhook_id}/test", response_model=WebhookDeliveryLogResponse)
async def test_webhook(
    tenant_id: uuid.UUID,
    webhook_id: uuid.UUID,
    data: WebhookTestRequest,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = WebhookService(db)
    try:
        return await service.test_webhook(tenant_id, webhook_id, data.event_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
